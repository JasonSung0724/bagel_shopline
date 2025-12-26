"""
Inventory service for parsing Excel files and managing inventory data.
"""
import io
import re
import pandas as pd
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from loguru import logger

from src.models.inventory import (
    InventoryItem,
    InventoryCategory,
    InventorySnapshot,
    InventoryRawItem,
)
from src.repositories.gmail_repository import GmailRepository
from src.models.email_attachment import EmailData


class InventoryService:
    """
    Service for inventory operations.
    - Fetch inventory emails from Gmail
    - Parse Excel attachments
    - Aggregate inventory data
    """

    # 品名分類規則
    BREAD_KEYWORDS = ['貝果', '歐包']
    BOX_KEYWORDS = ['紙箱', '禮盒', '包裝盒']
    BAG_KEYWORDS = ['塑膠袋', '袋']

    # 袋子每捲數量對照 (可擴充)
    BAG_ITEMS_PER_ROLL = {
        '小袋': 100,
        '中袋': 80,
        '大袋': 50,
        '保鮮袋': 200,
    }

    def __init__(self, gmail_repo: Optional[GmailRepository] = None):
        """Initialize inventory service."""
        self.gmail_repo = gmail_repo or GmailRepository()

    def fetch_inventory_emails(
        self,
        since_date: datetime,
        target_sender: Optional[str] = None
    ) -> List[EmailData]:
        """
        Fetch all inventory Excel emails since a given date.

        Args:
            since_date: Start date to search from
            target_sender: Optional sender filter (if None, searches all)

        Returns:
            List of EmailData with A442庫存明細 attachments
        """
        with self.gmail_repo as repo:
            # 搜尋所有郵件，過濾附件名稱包含 "A442庫存明細"
            emails = repo.fetch_emails_by_date(
                target_sender=target_sender or "",  # 如果沒指定，搜尋所有
                since_date=since_date,
                attachment_filter="A442庫存明細"
            )

        if emails:
            logger.success(f"找到 {len(emails)} 封庫存明細郵件")
        else:
            logger.info(f"沒有找到庫存明細郵件 (since {since_date.strftime('%Y-%m-%d')})")

        return emails

    def fetch_all_inventory_emails(
        self,
        target_sender: Optional[str] = None,
        days_back: int = 365
    ) -> List[EmailData]:
        """
        Fetch all historical inventory emails for backfill.

        Args:
            target_sender: Optional sender filter
            days_back: How many days back to search (default 1 year)

        Returns:
            List of EmailData sorted by date (oldest first)
        """
        from datetime import timedelta

        since_date = datetime.now() - timedelta(days=days_back)
        emails = self.fetch_inventory_emails(since_date, target_sender)

        # Sort by date (oldest first for chronological import)
        emails.sort(key=lambda e: e.date)

        logger.info(f"找到 {len(emails)} 封歷史庫存郵件，準備批次匯入")
        return emails

    def parse_inventory_excel(
        self,
        content: bytes,
        filename: str = ""
    ) -> InventorySnapshot:
        """
        Parse inventory Excel file and return aggregated snapshot.

        Args:
            content: Excel file content (bytes)
            filename: Source filename

        Returns:
            InventorySnapshot with parsed data (including raw items)
        """
        try:
            file = io.BytesIO(content)
            df = pd.read_excel(file)

            # 解析資料日期 (在清除空行之前)
            snapshot_date = self._extract_snapshot_date(df, filename)

            # 清除空行 (品名為空的列)
            df = df.dropna(subset=['品名'])

            # 解析原始資料 (每一列)
            raw_items = []
            for idx, row in df.iterrows():
                raw_item = InventoryRawItem.from_excel_row(
                    row.to_dict(),
                    row_number=idx + 2  # Excel 列號 (1-based, 加上標題列)
                )
                if raw_item.product_name:  # 跳過空品名
                    raw_items.append(raw_item)

            logger.info(f"解析原始資料: {len(raw_items)} 筆")

            # 按品名彙總庫存
            aggregated = self._aggregate_by_product(df)

            # 分類
            bread_items = []
            box_items = []
            bag_items = []

            for name, data in aggregated.items():
                category = self._categorize_product(name)
                item = self._create_inventory_item(name, category, data)

                if category == InventoryCategory.BREAD:
                    bread_items.append(item)
                elif category == InventoryCategory.BOX:
                    box_items.append(item)
                elif category == InventoryCategory.BAG:
                    bag_items.append(item)

            snapshot = InventorySnapshot(
                snapshot_date=snapshot_date,
                source_file=filename,
                bread_items=bread_items,
                box_items=box_items,
                bag_items=bag_items,
                raw_items=raw_items,  # 包含原始資料
            )

            logger.info(
                f"解析完成: {filename} - "
                f"原始 {len(raw_items)} 列, "
                f"麵包 {len(bread_items)} 項, "
                f"盒子 {len(box_items)} 項, "
                f"袋子 {len(bag_items)} 項"
            )

            return snapshot

        except Exception as e:
            logger.error(f"解析庫存 Excel 失敗: {e}")
            raise

    def _extract_snapshot_date(self, df: pd.DataFrame, filename: str) -> datetime:
        """Extract snapshot date from Excel data or filename."""
        # 嘗試從資料日期欄位取得
        if '資料日期' in df.columns:
            date_val = df['資料日期'].dropna().iloc[0] if not df['資料日期'].dropna().empty else None
            if date_val and isinstance(date_val, str):
                try:
                    # Format: "2025/12/25  20:02:39"
                    return datetime.strptime(date_val.strip(), "%Y/%m/%d  %H:%M:%S")
                except ValueError:
                    pass

        # 嘗試從檔名取得日期
        # Format: A442庫存明細20251225_251225200052.xls
        match = re.search(r'(\d{8})_', filename)
        if match:
            try:
                return datetime.strptime(match.group(1), "%Y%m%d")
            except ValueError:
                pass

        # 預設為當前時間
        return datetime.now()

    def _aggregate_by_product(self, df: pd.DataFrame) -> Dict[str, Dict]:
        """
        Aggregate inventory by product name.
        Same product with multiple batches should be summed.
        """
        aggregated = {}

        for _, row in df.iterrows():
            name = str(row.get('品名', '')).strip()
            if not name:
                continue

            period_end = float(row.get('期末', 0) or 0)
            available = float(row.get('預計可用量', 0) or 0)
            unit = str(row.get('單位', '個')).strip()

            if name not in aggregated:
                aggregated[name] = {
                    'period_end': 0,
                    'available': 0,
                    'unit': unit,
                }

            aggregated[name]['period_end'] += period_end
            aggregated[name]['available'] += available

        return aggregated

    def _categorize_product(self, name: str) -> InventoryCategory:
        """Categorize product by name."""
        # 檢查是否為袋子 (優先，因為有 "塑膠袋-xxx貝果")
        for keyword in self.BAG_KEYWORDS:
            if keyword in name:
                return InventoryCategory.BAG

        # 檢查是否為盒子
        for keyword in self.BOX_KEYWORDS:
            if keyword in name:
                return InventoryCategory.BOX

        # 檢查是否為麵包
        for keyword in self.BREAD_KEYWORDS:
            if keyword in name:
                return InventoryCategory.BREAD

        # 預設為麵包
        return InventoryCategory.BREAD

    def _create_inventory_item(
        self,
        name: str,
        category: InventoryCategory,
        data: Dict
    ) -> InventoryItem:
        """Create InventoryItem from aggregated data."""
        current_stock = int(data['period_end'])
        available_stock = int(data['available'])
        unit = data['unit']

        # 袋子特殊處理：設定每捲數量
        items_per_roll = None
        if category == InventoryCategory.BAG:
            unit = '捲'
            for bag_type, count in self.BAG_ITEMS_PER_ROLL.items():
                if bag_type in name:
                    items_per_roll = count
                    break

        return InventoryItem(
            name=name,
            category=category,
            current_stock=current_stock,
            available_stock=available_stock,
            unit=unit,
            items_per_roll=items_per_roll,
        )

    def process_email_attachment(
        self,
        email_data: EmailData
    ) -> Optional[InventorySnapshot]:
        """
        Process a single email and extract inventory snapshot.

        Args:
            email_data: EmailData with attachments

        Returns:
            InventorySnapshot or None if no valid attachment
        """
        for attachment in email_data.attachments:
            # 驗證檔名格式
            if not attachment.filename.startswith('A442庫存明細'):
                continue

            if not (attachment.filename.endswith('.xls') or
                    attachment.filename.endswith('.xlsx')):
                continue

            try:
                snapshot = self.parse_inventory_excel(
                    attachment.content,
                    attachment.filename
                )
                snapshot.source_email_date = email_data.date
                return snapshot
            except Exception as e:
                logger.error(f"處理附件 {attachment.filename} 失敗: {e}")
                continue

        return None

    def process_multiple_emails(
        self,
        emails: List[EmailData]
    ) -> List[InventorySnapshot]:
        """
        Process multiple emails and return all snapshots.
        Used for backfill.

        Args:
            emails: List of EmailData

        Returns:
            List of InventorySnapshot (sorted by date)
        """
        snapshots = []

        for email_data in emails:
            snapshot = self.process_email_attachment(email_data)
            if snapshot:
                snapshots.append(snapshot)

        # Sort by snapshot date
        snapshots.sort(key=lambda s: s.snapshot_date)

        logger.success(f"成功處理 {len(snapshots)}/{len(emails)} 封郵件")
        return snapshots

    def parse_local_excel(self, file_path: str) -> InventorySnapshot:
        """
        Parse a local Excel file (for testing or manual import).

        Args:
            file_path: Path to Excel file

        Returns:
            InventorySnapshot
        """
        import os

        with open(file_path, 'rb') as f:
            content = f.read()

        filename = os.path.basename(file_path)
        return self.parse_inventory_excel(content, filename)
