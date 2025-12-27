"""
Supabase repository for database operations.
"""
import os
from pathlib import Path
from typing import List, Optional, Dict, Any, TYPE_CHECKING
from datetime import datetime
from loguru import logger

if TYPE_CHECKING:
    from src.models.inventory import InventorySnapshot

# Load .env file
from dotenv import load_dotenv
_project_root = Path(__file__).resolve().parent.parent.parent
load_dotenv(_project_root / ".env")

try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    logger.warning("Supabase client not installed. Run: pip install supabase")


class SupabaseRepository:
    """
    Repository for Supabase database operations.

    Environment variables:
        SUPABASE_URL: Supabase project URL
        SUPABASE_KEY: Supabase anon/service key
    """

    def __init__(self):
        """Initialize Supabase client."""
        self.client: Optional[Client] = None

        if not SUPABASE_AVAILABLE:
            logger.warning("Supabase client not available")
            return

        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")

        if not url or not key:
            logger.warning("Supabase credentials not configured")
            return

        try:
            self.client = create_client(url, key)
            logger.info("Supabase client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase: {e}")

    @property
    def is_connected(self) -> bool:
        """Check if Supabase client is available."""
        return self.client is not None


class InventoryRepository(SupabaseRepository):
    """
    Repository for inventory data operations.

    Tables:
        - inventory_snapshots: 庫存快照
        - inventory_raw_items: Excel 原始資料
        - inventory_items: 庫存項目明細 (彙總)
        - inventory_changes: 庫存變動記錄
    """

    TABLE_SNAPSHOTS = "inventory_snapshots"
    TABLE_RAW_ITEMS = "inventory_raw_items"
    TABLE_ITEMS = "inventory_items"
    TABLE_CHANGES = "inventory_changes"

    def save_snapshot(self, snapshot: 'InventorySnapshot') -> Optional[str]:
        """
        Save an inventory snapshot to database.

        Args:
            snapshot: InventorySnapshot to save

        Returns:
            Snapshot ID or None if failed
        """
        if not self.is_connected:
            logger.warning("Supabase not connected, skipping save")
            return None

        try:
            # Check if snapshot for this date already exists
            existing = self._get_snapshot_by_date(snapshot.snapshot_date)
            if existing:
                logger.info(f"Snapshot for {snapshot.snapshot_date.date()} already exists, updating...")
                return self._update_snapshot(existing['id'], snapshot)

            # Insert snapshot record
            snapshot_data = {
                "snapshot_date": snapshot.snapshot_date.isoformat(),
                "source_file": snapshot.source_file,
                "source_email_date": snapshot.source_email_date.isoformat() if snapshot.source_email_date else None,
                "total_bread_stock": snapshot.total_bread_stock,
                "total_box_stock": snapshot.total_box_stock,
                "total_bag_rolls": snapshot.total_bag_rolls,
                "low_stock_count": snapshot.low_stock_count,
                "raw_item_count": len(snapshot.raw_items) if snapshot.raw_items else 0,
            }

            result = self.client.table(self.TABLE_SNAPSHOTS).insert(snapshot_data).execute()

            if not result.data:
                logger.error("Failed to insert snapshot")
                return None

            snapshot_id = result.data[0]['id']

            # Insert raw items (原始資料)
            self._save_raw_items(snapshot_id, snapshot)

            # Insert inventory items (彙總資料)
            self._save_items(snapshot_id, snapshot)

            logger.success(f"Saved snapshot {snapshot_id} for {snapshot.snapshot_date.date()}")
            return snapshot_id

        except Exception as e:
            logger.error(f"Failed to save snapshot: {e}")
            return None

    def _get_snapshot_by_date(self, date: datetime) -> Optional[Dict]:
        """Get snapshot by date (same day)."""
        try:
            date_str = date.date().isoformat()
            result = self.client.table(self.TABLE_SNAPSHOTS) \
                .select("*") \
                .gte("snapshot_date", f"{date_str}T00:00:00") \
                .lt("snapshot_date", f"{date_str}T23:59:59") \
                .execute()

            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Failed to check existing snapshot: {e}")
            return None

    def _update_snapshot(self, snapshot_id: str, snapshot: 'InventorySnapshot') -> str:
        """Update existing snapshot."""
        try:
            # Update snapshot record
            snapshot_data = {
                "source_file": snapshot.source_file,
                "source_email_date": snapshot.source_email_date.isoformat() if snapshot.source_email_date else None,
                "total_bread_stock": snapshot.total_bread_stock,
                "total_box_stock": snapshot.total_box_stock,
                "total_bag_rolls": snapshot.total_bag_rolls,
                "low_stock_count": snapshot.low_stock_count,
                "updated_at": datetime.now().isoformat(),
            }

            self.client.table(self.TABLE_SNAPSHOTS) \
                .update(snapshot_data) \
                .eq("id", snapshot_id) \
                .execute()

            # Delete old items and re-insert
            self.client.table(self.TABLE_ITEMS) \
                .delete() \
                .eq("snapshot_id", snapshot_id) \
                .execute()

            self._save_items(snapshot_id, snapshot)

            return snapshot_id

        except Exception as e:
            logger.error(f"Failed to update snapshot: {e}")
            return snapshot_id

    def _save_raw_items(self, snapshot_id: str, snapshot: 'InventorySnapshot') -> None:
        """Save raw inventory items (original Excel rows) for a snapshot."""
        if not snapshot.raw_items:
            return

        # 分批插入 (每批 100 筆，避免請求過大)
        batch_size = 100
        raw_items_data = []

        for raw_item in snapshot.raw_items:
            item_data = raw_item.to_dict()
            item_data["snapshot_id"] = snapshot_id
            # 將 raw_data 轉為 JSON 字串（如果是 dict）
            if item_data.get("raw_data") and isinstance(item_data["raw_data"], dict):
                import json
                # 清理 NaN 值
                cleaned = {k: (None if (isinstance(v, float) and str(v) == 'nan') else v)
                          for k, v in item_data["raw_data"].items()}
                item_data["raw_data"] = json.dumps(cleaned, ensure_ascii=False, default=str)
            raw_items_data.append(item_data)

        # 分批插入
        for i in range(0, len(raw_items_data), batch_size):
            batch = raw_items_data[i:i + batch_size]
            try:
                self.client.table(self.TABLE_RAW_ITEMS).insert(batch).execute()
            except Exception as e:
                logger.error(f"Failed to insert raw items batch {i//batch_size + 1}: {e}")

        logger.info(f"Saved {len(raw_items_data)} raw items for snapshot")

    def _save_items(self, snapshot_id: str, snapshot: 'InventorySnapshot') -> None:
        """Save aggregated inventory items for a snapshot."""
        all_items = []

        for item in snapshot.bread_items + snapshot.box_items + snapshot.bag_items:
            all_items.append({
                "snapshot_id": snapshot_id,
                "name": item.name,
                "category": item.category.value,
                "current_stock": item.current_stock,
                "available_stock": item.available_stock,
                "unit": item.unit,
                "min_stock": item.min_stock,
                "items_per_roll": item.items_per_roll,
                "stock_status": item.stock_status,
            })

        if all_items:
            self.client.table(self.TABLE_ITEMS).insert(all_items).execute()

    def get_latest_snapshot(self) -> Optional[Dict]:
        """
        Get the most recent inventory snapshot.

        Returns:
            Snapshot data with items or None
        """
        if not self.is_connected:
            logger.warning("Supabase not connected")
            return None

        try:
            # Get latest snapshot
            result = self.client.table(self.TABLE_SNAPSHOTS) \
                .select("*") \
                .order("snapshot_date", desc=True) \
                .limit(1) \
                .execute()

            if not result.data:
                return None

            snapshot = result.data[0]

            # Get items for this snapshot
            items_result = self.client.table(self.TABLE_ITEMS) \
                .select("*") \
                .eq("snapshot_id", snapshot['id']) \
                .execute()

            # Organize items by category
            snapshot['bread_items'] = [i for i in items_result.data if i['category'] == 'bread']
            snapshot['box_items'] = [i for i in items_result.data if i['category'] == 'box']
            snapshot['bag_items'] = [i for i in items_result.data if i['category'] == 'bag']

            return snapshot

        except Exception as e:
            logger.error(f"Failed to get latest snapshot: {e}")
            return None

    def get_snapshots_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict]:
        """
        Get snapshots within a date range.

        Args:
            start_date: Start of date range
            end_date: End of date range

        Returns:
            List of snapshots
        """
        if not self.is_connected:
            return []

        try:
            result = self.client.table(self.TABLE_SNAPSHOTS) \
                .select("*") \
                .gte("snapshot_date", start_date.isoformat()) \
                .lte("snapshot_date", end_date.isoformat()) \
                .order("snapshot_date", desc=True) \
                .execute()

            return result.data or []

        except Exception as e:
            logger.error(f"Failed to get snapshots by date range: {e}")
            return []

    def save_inventory_change(
        self,
        item_name: str,
        category: str,
        previous_stock: int,
        new_stock: int,
        source: str = "email"
    ) -> Optional[str]:
        """
        Record an inventory change.

        Returns:
            Change record ID or None
        """
        if not self.is_connected:
            return None

        try:
            change_data = {
                "date": datetime.now().isoformat(),
                "item_name": item_name,
                "category": category,
                "previous_stock": previous_stock,
                "new_stock": new_stock,
                "change_amount": new_stock - previous_stock,
                "source": source,
            }

            result = self.client.table(self.TABLE_CHANGES).insert(change_data).execute()
            return result.data[0]['id'] if result.data else None

        except Exception as e:
            logger.error(f"Failed to save inventory change: {e}")
            return None

    def get_recent_changes(self, limit: int = 20) -> List[Dict]:
        """
        Get recent inventory changes.

        Args:
            limit: Number of records to return

        Returns:
            List of change records
        """
        if not self.is_connected:
            return []

        try:
            result = self.client.table(self.TABLE_CHANGES) \
                .select("*") \
                .order("date", desc=True) \
                .limit(limit) \
                .execute()

            return result.data or []

        except Exception as e:
            logger.error(f"Failed to get recent changes: {e}")
            return []

    def get_item_history(
        self,
        item_name: str,
        days: int = 30
    ) -> List[Dict]:
        """
        Get stock history for a specific item.

        Args:
            item_name: Item name
            days: Number of days to look back

        Returns:
            List of historical stock values
        """
        if not self.is_connected:
            return []

        try:
            from datetime import timedelta
            start_date = datetime.now() - timedelta(days=days)

            result = self.client.table(self.TABLE_ITEMS) \
                .select("*, inventory_snapshots(snapshot_date)") \
                .eq("name", item_name) \
                .gte("created_at", start_date.isoformat()) \
                .order("created_at") \
                .execute()

            return result.data or []

        except Exception as e:
            logger.error(f"Failed to get item history: {e}")
            return []

    def get_items_trend(
        self,
        category: Optional[str] = None,
        days: int = 30
    ) -> List[Dict]:
        """
        Get daily stock trend for items (for charts).

        Args:
            category: Filter by category ('bread', 'box', 'bag') - optional
            days: Number of days to look back

        Returns:
            List of items with their daily stock values:
            [
                {
                    "name": "低糖原味貝果",
                    "category": "bread",
                    "data": [
                        {"date": "2025-12-25", "stock": 5000},
                        {"date": "2025-12-26", "stock": 4800},
                        ...
                    ]
                },
                ...
            ]
        """
        if not self.is_connected:
            return []

        try:
            from datetime import timedelta
            start_date = datetime.now() - timedelta(days=days)

            # Query all items with their snapshot dates
            # Use available_stock (預計可用量) instead of current_stock (期末)
            query = self.client.table(self.TABLE_ITEMS) \
                .select("name, category, available_stock, inventory_snapshots(snapshot_date)") \
                .gte("created_at", start_date.isoformat())

            if category:
                query = query.eq("category", category)

            result = query.order("created_at").execute()

            if not result.data:
                return []

            # Group by item name
            items_data: Dict[str, Dict] = {}
            for row in result.data:
                name = row['name']
                if name not in items_data:
                    items_data[name] = {
                        'name': name,
                        'category': row['category'],
                        'data': []
                    }

                # Extract snapshot date
                snapshot_info = row.get('inventory_snapshots')
                if snapshot_info and snapshot_info.get('snapshot_date'):
                    date_str = snapshot_info['snapshot_date'][:10]  # YYYY-MM-DD
                    items_data[name]['data'].append({
                        'date': date_str,
                        'stock': row['available_stock']  # Use available_stock (預計可用量)
                    })

            return list(items_data.values())

        except Exception as e:
            logger.error(f"Failed to get items trend: {e}")
            return []

    def get_sales_trend(
        self,
        category: Optional[str] = None,
        days: int = 30
    ) -> List[Dict]:
        """
        Get daily sales trend for items (based on stock_out from raw items).

        Args:
            category: Filter by category ('bread', 'box', 'bag') - optional
            days: Number of days to look back

        Returns:
            List of items with their daily sales (stock_out) values:
            [
                {
                    "name": "低糖原味貝果",
                    "category": "bread",
                    "data": [
                        {"date": "2025-12-25", "sales": 200},
                        {"date": "2025-12-26", "sales": 150},
                        ...
                    ]
                },
                ...
            ]
        """
        if not self.is_connected:
            return []

        try:
            from datetime import timedelta
            start_date = datetime.now() - timedelta(days=days)

            # Query raw items with stock_out data
            query = self.client.table(self.TABLE_RAW_ITEMS) \
                .select("product_name, stock_out, snapshot_id, inventory_snapshots(snapshot_date)") \
                .gte("created_at", start_date.isoformat())

            result = query.order("created_at").execute()

            if not result.data:
                return []

            # Get category mapping from inventory_items
            category_map = {}
            if category:
                # Filter by category - need to get items in that category first
                items_result = self.client.table(self.TABLE_ITEMS) \
                    .select("name, category") \
                    .eq("category", category) \
                    .execute()
                if items_result.data:
                    category_map = {item['name']: item['category'] for item in items_result.data}
            else:
                # Get all category mappings
                items_result = self.client.table(self.TABLE_ITEMS) \
                    .select("name, category") \
                    .execute()
                if items_result.data:
                    category_map = {item['name']: item['category'] for item in items_result.data}

            # Group by product name and date, sum stock_out
            items_data: Dict[str, Dict] = {}
            for row in result.data:
                name = row['product_name']

                # Filter by category if specified
                if category and name not in category_map:
                    continue

                if name not in items_data:
                    items_data[name] = {
                        'name': name,
                        'category': category_map.get(name, 'bread'),
                        'data': {}  # Use dict to aggregate by date
                    }

                # Extract snapshot date
                snapshot_info = row.get('inventory_snapshots')
                if snapshot_info and snapshot_info.get('snapshot_date'):
                    date_str = snapshot_info['snapshot_date'][:10]  # YYYY-MM-DD
                    stock_out = row.get('stock_out', 0) or 0

                    # Aggregate stock_out by date (same product may have multiple batches)
                    if date_str not in items_data[name]['data']:
                        items_data[name]['data'][date_str] = 0
                    items_data[name]['data'][date_str] += stock_out

            # Convert dict to list format
            result_list = []
            for name, item in items_data.items():
                data_list = [
                    {'date': date, 'sales': int(sales)}
                    for date, sales in sorted(item['data'].items())
                ]
                if data_list:  # Only include items with data
                    result_list.append({
                        'name': name,
                        'category': item['category'],
                        'data': data_list
                    })

            return result_list

        except Exception as e:
            logger.error(f"Failed to get sales trend: {e}")
            return []
