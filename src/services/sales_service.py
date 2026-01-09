"""
Sales Service
處理銷售資料（來自逢泰 A442_QC Excel 的「實出量」欄位）
"""

import io
import pandas as pd
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
from loguru import logger

from src.models.email_attachment import EmailData
from src.repositories.supabase_repository import SupabaseRepository


class SalesService:
    """處理銷售資料的服務"""

    # Excel 欄位對應
    EXCEL_COLUMN_MAPPING = {
        "出貨日": "sale_date",
        "品名": "product_name",
        "實出量": "quantity",  # 實出量 = 銷量
    }

    # 品項分類關鍵字（與 inventory_service 保持一致）
    BREAD_KEYWORDS = ['貝果', '歐包', '吐司', '麵包']
    BOX_KEYWORDS = ['紙箱', '禮盒', '包裝盒', '盒']

    def __init__(self):
        """初始化 Sales Service"""
        self.repo = SupabaseRepository()

    def parse_sales_excel(self, content: bytes, filename: str = "") -> Tuple[datetime, Dict[str, Dict]]:
        """
        解析銷售 Excel，彙總每個品項的實出量

        Args:
            content: Excel 檔案內容
            filename: 檔案名稱（用於除錯）

        Returns:
            (sale_date, sales_data)
            sale_date: 銷售日期
            sales_data: {
                "品名": {
                    "quantity": 總銷量,
                    "category": "bread" or "box"
                }
            }
        """
        logger.info(f"解析銷售 Excel: {filename}")

        try:
            # 讀取 Excel
            file = io.BytesIO(content)
            df = pd.read_excel(file)

            logger.info(f"Excel 欄位: {list(df.columns)}")
            logger.info(f"總共 {len(df)} 列資料")

            # 檢查必要欄位
            required_columns = ["出貨日", "品名", "實出量"]
            missing_columns = [col for col in required_columns if col not in df.columns]

            if missing_columns:
                raise ValueError(f"Excel 缺少必要欄位: {missing_columns}")

            # 提取銷售日期（從第一筆資料）
            sale_date = self._extract_sale_date(df, filename)
            logger.info(f"銷售日期: {sale_date.strftime('%Y-%m-%d')}")

            # 移除空行
            df = df.dropna(subset=['品名'])

            # 彙總銷量
            sales_data = self._aggregate_sales(df)
            logger.success(f"解析完成，共 {len(sales_data)} 個品項")

            return sale_date, sales_data

        except Exception as e:
            logger.error(f"解析 Excel 失敗: {e}")
            raise

    def _extract_sale_date(self, df: pd.DataFrame, filename: str) -> datetime:
        """
        提取銷售日期

        優先級：
        1. Excel 中「出貨日」欄位的值
        2. 檔名中的日期
        3. 當前時間

        Args:
            df: DataFrame
            filename: 檔案名稱

        Returns:
            銷售日期
        """
        # 1. 從「出貨日」欄位取得
        if '出貨日' in df.columns and not df['出貨日'].dropna().empty:
            date_val = df['出貨日'].dropna().iloc[0]

            try:
                # 格式: 20260107
                if isinstance(date_val, (int, float)):
                    date_str = str(int(date_val))
                    return datetime.strptime(date_str, "%Y%m%d")
                elif isinstance(date_val, str):
                    # 嘗試不同格式
                    for fmt in ["%Y%m%d", "%Y/%m/%d", "%Y-%m-%d"]:
                        try:
                            return datetime.strptime(date_val.strip(), fmt)
                        except ValueError:
                            continue
            except Exception as e:
                logger.warning(f"無法解析出貨日期: {e}")

        # 2. 從檔名取得日期
        # 格式: A442_QC_20260107_260107200007.xls
        import re
        match = re.search(r'(\d{8})', filename)
        if match:
            try:
                return datetime.strptime(match.group(1), "%Y%m%d")
            except ValueError:
                pass

        # 3. 預設為當前時間
        logger.warning("無法從 Excel 或檔名取得日期，使用當前時間")
        return datetime.now()

    def _aggregate_sales(self, df: pd.DataFrame) -> Dict[str, Dict]:
        """
        按品名彙總銷量

        Args:
            df: DataFrame

        Returns:
            {
                "品名": {
                    "quantity": 總銷量,
                    "category": "bread" or "box"
                }
            }
        """
        sales_data = {}

        for _, row in df.iterrows():
            product_name = str(row.get('品名', '')).strip()
            if not product_name:
                continue

            # 取得實出量（銷量）
            quantity = row.get('實出量', 0)
            try:
                quantity = float(quantity) if pd.notna(quantity) else 0
            except (ValueError, TypeError):
                quantity = 0

            # 分類品項
            category = self._categorize_product(product_name)

            # 彙總同品名的銷量
            if product_name not in sales_data:
                sales_data[product_name] = {
                    'quantity': 0,
                    'category': category
                }

            sales_data[product_name]['quantity'] += quantity

        return sales_data

    def _categorize_product(self, product_name: str) -> str:
        """
        根據品名分類

        Args:
            product_name: 品名

        Returns:
            'bread' or 'box'
        """
        name_lower = product_name.lower()

        # 檢查是否為盒子
        if any(keyword in product_name for keyword in self.BOX_KEYWORDS):
            return 'box'

        # 檢查是否為麵包
        if any(keyword in product_name for keyword in self.BREAD_KEYWORDS):
            return 'bread'

        # 預設為麵包
        return 'bread'

    def save_daily_sales(self, sale_date: datetime, sales_data: Dict[str, Dict]) -> bool:
        """
        儲存每日銷量資料

        1. 更新 master_sales_products（自動新增新品項）
        2. 儲存 daily_sales（含零銷量記錄）

        Args:
            sale_date: 銷售日期
            sales_data: 銷量資料

        Returns:
            True if successful
        """
        try:
            date_str = sale_date.strftime('%Y-%m-%d')
            logger.info(f"開始儲存 {date_str} 的銷量資料")

            # 1. 更新 master_sales_products
            self._update_master_products(sale_date, sales_data)

            # 2. 取得所有應該記錄的商品（包含歷史商品）
            all_products = self.repo.get_master_sales_products()

            # 3. 建立 daily_sales 資料
            daily_sales_records = []

            for product in all_products:
                product_name = product['product_name']
                category = product['category']

                # 如果今天有銷量，使用實際銷量；否則記錄為 0
                quantity = sales_data.get(product_name, {}).get('quantity', 0)

                daily_sales_records.append({
                    'sale_date': date_str,
                    'product_name': product_name,
                    'category': category,
                    'quantity': quantity,
                    'source': 'flowtide_qc'
                })

            # 4. 批次儲存到資料庫（使用 upsert）
            self.repo.save_daily_sales_batch(daily_sales_records)

            logger.success(f"成功儲存 {len(daily_sales_records)} 筆銷量記錄")
            return True

        except Exception as e:
            logger.error(f"儲存銷量資料失敗: {e}")
            return False

    def _update_master_products(self, sale_date: datetime, sales_data: Dict[str, Dict]):
        """
        更新 master_sales_products

        - 新品項：自動新增
        - 現有品項：更新 last_seen_date

        Args:
            sale_date: 銷售日期
            sales_data: 銷量資料
        """
        logger.info("更新 master_sales_products...")

        # 取得現有商品
        existing_products = self.repo.get_master_sales_products()
        existing_names = {p['product_name'] for p in existing_products}

        # 準備要新增/更新的商品
        products_to_upsert = []

        for product_name, data in sales_data.items():
            if data['quantity'] == 0:
                # 跳過零銷量（不更新 master_sales_products）
                continue

            if product_name in existing_names:
                # 更新 last_seen_date
                products_to_upsert.append({
                    'product_name': product_name,
                    'category': data['category'],
                    'last_seen_date': sale_date.strftime('%Y-%m-%d'),
                    'is_active': True
                })
            else:
                # 新增商品
                logger.info(f"發現新商品: {product_name} ({data['category']})")
                products_to_upsert.append({
                    'product_name': product_name,
                    'category': data['category'],
                    'first_seen_date': sale_date.strftime('%Y-%m-%d'),
                    'last_seen_date': sale_date.strftime('%Y-%m-%d'),
                    'is_active': True
                })

        # 批次 upsert
        if products_to_upsert:
            self.repo.upsert_master_sales_products(products_to_upsert)
            logger.success(f"更新了 {len(products_to_upsert)} 個商品到 master_sales_products")

    def process_sales_from_emails(self, emails: List[EmailData]) -> Tuple[int, int]:
        """
        從郵件中處理銷售資料

        Args:
            emails: 郵件列表

        Returns:
            (成功處理數, 失敗數)
        """
        success_count = 0
        fail_count = 0

        for email in emails:
            # 取得逢泰出貨 Excel
            qc_attachments = email.get_flowtide_attachments()

            for attachment in qc_attachments:
                try:
                    logger.info(f"處理附件: {attachment.filename}")

                    # 解析 Excel
                    sale_date, sales_data = self.parse_sales_excel(
                        attachment.content,
                        attachment.filename
                    )

                    # 儲存銷量資料
                    if self.save_daily_sales(sale_date, sales_data):
                        success_count += 1
                    else:
                        fail_count += 1

                except Exception as e:
                    logger.error(f"處理附件失敗 {attachment.filename}: {e}")
                    fail_count += 1

        return success_count, fail_count

    def backfill(
        self,
        days_back: int = 30,
        start_days_ago: int = 0,
        dry_run: bool = False
    ) -> Tuple[int, int]:
        """
        回填歷史銷量資料

        Args:
            days_back: 回溯天數
            start_days_ago: 從 N 天前開始回溯
            dry_run: True = 只解析不保存到資料庫

        Returns:
            (成功處理數, 失敗數)
        """
        from src.services.email_service import EmailService

        email_service = EmailService()

        # 計算日期範圍
        end_date = datetime.now() - timedelta(days=start_days_ago)
        start_date = end_date - timedelta(days=days_back)

        logger.info(f"回填日期範圍: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
        if dry_run:
            logger.info("[DRY RUN] 不會保存到資料庫")

        # 逐日抓取郵件
        all_emails = []
        current_date = start_date

        while current_date <= end_date:
            try:
                emails = email_service.fetch_flowtide_emails(current_date)
                if emails:
                    all_emails.extend(emails)
                    logger.info(f"{current_date.strftime('%Y-%m-%d')}: 找到 {len(emails)} 封郵件")
            except Exception as e:
                logger.warning(f"{current_date.strftime('%Y-%m-%d')}: 抓取郵件失敗 - {e}")

            current_date += timedelta(days=1)

        if not all_emails:
            logger.warning("沒有找到符合條件的郵件")
            return 0, 0

        logger.info(f"總共找到 {len(all_emails)} 封郵件")

        # 處理每封郵件
        total_success = 0
        total_fail = 0

        for email in all_emails:
            qc_attachments = email.get_flowtide_attachments()

            for attachment in qc_attachments:
                try:
                    logger.info(f"處理附件: {attachment.filename}")

                    # 解析 Excel
                    sale_date, sales_data = self.parse_sales_excel(
                        attachment.content,
                        attachment.filename
                    )

                    if dry_run:
                        logger.info(f"[DRY RUN] 解析成功: {sale_date.strftime('%Y-%m-%d')}, {len(sales_data)} 個品項")
                        total_success += 1
                    else:
                        if self.save_daily_sales(sale_date, sales_data):
                            total_success += 1
                        else:
                            total_fail += 1

                except Exception as e:
                    logger.error(f"處理附件失敗 {attachment.filename}: {e}")
                    total_fail += 1

        logger.info("=" * 50)
        logger.info(f"回填完成: 成功 {total_success} 個, 失敗 {total_fail} 個")
        logger.info("=" * 50)

        return total_success, total_fail
