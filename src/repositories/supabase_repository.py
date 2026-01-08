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
    TABLE_MAPPINGS = "product_mappings"
    TABLE_MASTER_BREADS = "master_breads"
    TABLE_MASTER_BAGS = "master_bags"
    TABLE_MASTER_BOXES = "master_boxes"
    TABLE_MASTER_SALES_PRODUCTS = "master_sales_products"
    TABLE_DAILY_SALES = "daily_sales"

    def save_snapshot(self, snapshot: "InventorySnapshot") -> Optional[str]:
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
                return self._update_snapshot(existing["id"], snapshot)

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

            snapshot_id = result.data[0]["id"]

            # Insert raw items (原始資料)
            self._save_raw_items(snapshot_id, snapshot)

            # Insert inventory items (彙總資料)
            self._save_items(snapshot_id, snapshot)

            # Auto-sync new items to master tables (自動同步新品項)
            self._auto_sync_master_data(snapshot)

            logger.success(f"Saved snapshot {snapshot_id} for {snapshot.snapshot_date.date()}")
            return snapshot_id

        except Exception as e:
            logger.error(f"Failed to save snapshot: {e}")
            return None

    def _get_snapshot_by_date(self, date: datetime) -> Optional[Dict]:
        """Get snapshot by date (same day)."""
        try:
            date_str = date.date().isoformat()
            result = (
                self.client.table(self.TABLE_SNAPSHOTS)
                .select("*")
                .gte("snapshot_date", f"{date_str}T00:00:00")
                .lt("snapshot_date", f"{date_str}T23:59:59")
                .execute()
            )

            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Failed to check existing snapshot: {e}")
            return None

    def _update_snapshot(self, snapshot_id: str, snapshot: "InventorySnapshot") -> str:
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

            self.client.table(self.TABLE_SNAPSHOTS).update(snapshot_data).eq("id", snapshot_id).execute()

            # Delete old items and re-insert
            self.client.table(self.TABLE_ITEMS).delete().eq("snapshot_id", snapshot_id).execute()

            self._save_items(snapshot_id, snapshot)

            return snapshot_id

        except Exception as e:
            logger.error(f"Failed to update snapshot: {e}")
            return snapshot_id

    def _save_raw_items(self, snapshot_id: str, snapshot: "InventorySnapshot") -> None:
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
                cleaned = {k: (None if (isinstance(v, float) and str(v) == "nan") else v) for k, v in item_data["raw_data"].items()}
                item_data["raw_data"] = json.dumps(cleaned, ensure_ascii=False, default=str)
            raw_items_data.append(item_data)

        # 分批插入
        for i in range(0, len(raw_items_data), batch_size):
            batch = raw_items_data[i : i + batch_size]
            try:
                self.client.table(self.TABLE_RAW_ITEMS).insert(batch).execute()
            except Exception as e:
                logger.error(f"Failed to insert raw items batch {i//batch_size + 1}: {e}")

        logger.info(f"Saved {len(raw_items_data)} raw items for snapshot")

    def _save_items(self, snapshot_id: str, snapshot: "InventorySnapshot") -> None:
        """Save aggregated inventory items for a snapshot."""
        all_items = []

        for item in snapshot.bread_items + snapshot.box_items + snapshot.bag_items:
            all_items.append(
                {
                    "snapshot_id": snapshot_id,
                    "name": item.name,
                    "category": item.category.value,
                    "current_stock": item.current_stock,
                    "available_stock": item.available_stock,
                    "unit": item.unit,
                    "min_stock": item.min_stock,
                    "items_per_roll": item.items_per_roll,
                    "stock_status": item.stock_status,
                }
            )

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
            result = self.client.table(self.TABLE_SNAPSHOTS).select("*").order("snapshot_date", desc=True).limit(1).execute()

            if not result.data:
                return None

            snapshot = result.data[0]

            # Get items for this snapshot
            items_result = self.client.table(self.TABLE_ITEMS).select("*").eq("snapshot_id", snapshot["id"]).execute()

            # Organize items by category
            snapshot["bread_items"] = [i for i in items_result.data if i["category"] == "bread"]
            snapshot["box_items"] = [i for i in items_result.data if i["category"] == "box"]
            snapshot["bag_items"] = [i for i in items_result.data if i["category"] == "bag"]

            return snapshot

        except Exception as e:
            logger.error(f"Failed to get latest snapshot: {e}")
            return None

    def get_snapshots_by_date_range(self, start_date: datetime, end_date: datetime) -> List[Dict]:
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
            result = (
                self.client.table(self.TABLE_SNAPSHOTS)
                .select("*")
                .gte("snapshot_date", start_date.isoformat())
                .lte("snapshot_date", end_date.isoformat())
                .order("snapshot_date", desc=True)
                .execute()
            )

            return result.data or []

        except Exception as e:
            logger.error(f"Failed to get snapshots by date range: {e}")
            return []

    def save_inventory_change(self, item_name: str, category: str, previous_stock: int, new_stock: int, source: str = "email") -> Optional[str]:
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
            return result.data[0]["id"] if result.data else None

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
            result = self.client.table(self.TABLE_CHANGES).select("*").order("date", desc=True).limit(limit).execute()

            return result.data or []

        except Exception as e:
            logger.error(f"Failed to get recent changes: {e}")
            return []

    def get_item_history(self, item_name: str, days: int = 30) -> List[Dict]:
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

            result = (
                self.client.table(self.TABLE_ITEMS)
                .select("*, inventory_snapshots(snapshot_date)")
                .eq("name", item_name)
                .gte("created_at", start_date.isoformat())
                .order("created_at")
                .execute()
            )

            return result.data or []

        except Exception as e:
            logger.error(f"Failed to get item history: {e}")
            return []

    def get_items_trend(self, category: Optional[str] = None, days: int = 30) -> List[Dict]:
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
            query = (
                self.client.table(self.TABLE_ITEMS)
                .select("name, category, available_stock, inventory_snapshots(snapshot_date)")
                .gte("created_at", start_date.isoformat())
            )

            if category:
                query = query.eq("category", category)

            result = query.order("created_at").execute()

            if not result.data:
                return []

            # Group by item name
            items_data: Dict[str, Dict] = {}
            for row in result.data:
                name = row["name"]
                if name not in items_data:
                    items_data[name] = {"name": name, "category": row["category"], "data": []}

                # Extract snapshot date
                snapshot_info = row.get("inventory_snapshots")
                if snapshot_info and snapshot_info.get("snapshot_date"):
                    date_str = snapshot_info["snapshot_date"][:10]  # YYYY-MM-DD
                    items_data[name]["data"].append({"date": date_str, "stock": row["available_stock"]})  # Use available_stock (預計可用量)

            return list(items_data.values())

        except Exception as e:
            logger.error(f"Failed to get items trend: {e}")
            return []

    def get_sales_trend(self, category: Optional[str] = None, days: int = 30) -> List[Dict]:
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

            start_date = (datetime.now() - timedelta(days=days)).date().isoformat()

            # First, get snapshot IDs within the date range
            snapshots_result = self.client.table(self.TABLE_SNAPSHOTS).select("id, snapshot_date").gte("snapshot_date", start_date).execute()

            if not snapshots_result.data:
                return []

            # Create a map of snapshot_id -> date
            snapshot_date_map = {s["id"]: s["snapshot_date"][:10] for s in snapshots_result.data}
            snapshot_ids = list(snapshot_date_map.keys())

            # Query raw items for these snapshots
            # Note: Supabase .in_() has URL length limits with many UUIDs,
            # so we batch snapshot IDs (max 10 per batch) to avoid truncation
            all_raw_items = []
            batch_size = 10

            for i in range(0, len(snapshot_ids), batch_size):
                batch_ids = snapshot_ids[i:i + batch_size]

                # Paginate within each batch
                page_size = 1000
                offset = 0

                while True:
                    result = (
                        self.client.table(self.TABLE_RAW_ITEMS)
                        .select("product_name, stock_out, snapshot_id")
                        .in_("snapshot_id", batch_ids)
                        .range(offset, offset + page_size - 1)
                        .execute()
                    )

                    if not result.data:
                        break

                    all_raw_items.extend(result.data)

                    if len(result.data) < page_size:
                        break

                    offset += page_size

            if not all_raw_items:
                return []

            result_data = all_raw_items

            # Get category mapping from inventory_items
            category_map = {}
            if category:
                # Filter by category - need to get items in that category first
                items_result = self.client.table(self.TABLE_ITEMS).select("name, category").eq("category", category).execute()
                if items_result.data:
                    category_map = {item["name"]: item["category"] for item in items_result.data}
            else:
                # Get all category mappings
                items_result = self.client.table(self.TABLE_ITEMS).select("name, category").execute()
                if items_result.data:
                    category_map = {item["name"]: item["category"] for item in items_result.data}

            # Group by product name and date, sum stock_out
            items_data: Dict[str, Dict] = {}
            for row in result_data:
                name = row["product_name"]

                # Filter by category if specified
                if category and name not in category_map:
                    continue

                if name not in items_data:
                    items_data[name] = {"name": name, "category": category_map.get(name, "bread"), "data": {}}  # Use dict to aggregate by date

                # Get date from snapshot_id
                snapshot_id = row.get("snapshot_id")
                date_str = snapshot_date_map.get(snapshot_id)
                if date_str:
                    stock_out = row.get("stock_out", 0) or 0

                    # Aggregate stock_out by date (same product may have multiple batches)
                    if date_str not in items_data[name]["data"]:
                        items_data[name]["data"][date_str] = 0
                    items_data[name]["data"][date_str] += stock_out

            # Convert dict to list format
            result_list = []
            for name, item in items_data.items():
                data_list = [{"date": date, "sales": int(sales)} for date, sales in sorted(item["data"].items())]
                if data_list:  # Only include items with data
                    result_list.append({"name": name, "category": item["category"], "data": data_list})

            return result_list

        except Exception as e:
            logger.error(f"Failed to get sales trend: {e}")
            return []

    def get_restock_records(self, days: int = 30, category: Optional[str] = None) -> List[Dict]:
        """
        Get restock records (入庫) from raw items.

        Args:
            days: Number of days to look back
            category: Filter by category ('bread', 'box', 'bag') - optional

        Returns:
            List of restock records:
            [
                {
                    "date": "2025-12-25",
                    "product_name": "低糖原味貝果",
                    "category": "bread",
                    "stock_in": 500,
                    "expiry_date": "2026-01-25",
                    "warehouse_date": "2025-12-25"
                },
                ...
            ]
        """
        if not self.is_connected:
            return []

        try:
            from datetime import timedelta

            start_date = datetime.now() - timedelta(days=days)

            # Query raw items with stock_in > 0
            query = (
                self.client.table(self.TABLE_RAW_ITEMS)
                .select("product_name, stock_in, expiry_date, warehouse_date, snapshot_id, inventory_snapshots(snapshot_date)")
                .gt("stock_in", 0)
                .gte("created_at", start_date.isoformat())
            )

            result = query.order("created_at", desc=True).execute()

            if not result.data:
                return []

            # Get category mapping from inventory_items
            category_map = {}
            items_result = self.client.table(self.TABLE_ITEMS).select("name, category").execute()
            if items_result.data:
                category_map = {item["name"]: item["category"] for item in items_result.data}

            # Transform data
            records = []
            for row in result.data:
                name = row["product_name"]
                item_category = category_map.get(name, "bread")

                # Filter by category if specified
                if category and item_category != category:
                    continue

                # Extract snapshot date
                snapshot_info = row.get("inventory_snapshots")
                date_str = None
                if snapshot_info and snapshot_info.get("snapshot_date"):
                    date_str = snapshot_info["snapshot_date"][:10]  # YYYY-MM-DD

                records.append(
                    {
                        "date": date_str or row.get("warehouse_date", ""),
                        "product_name": name,
                        "category": item_category,
                        "stock_in": int(row.get("stock_in", 0)),
                        "expiry_date": row.get("expiry_date"),
                        "warehouse_date": row.get("warehouse_date"),
                    }
                )

            return records

        except Exception as e:
            logger.error(f"Failed to get restock records: {e}")
            return []

    def get_product_mappings(self) -> List[Dict]:
        """
        Get product mappings (bread to bag relationships).

        Returns:
            List of mappings: [
                {
                    "bread_name": "西西里開心果乳酪貝果",
                    "bag_name": "塑膠袋-開心果乳酪貝果"
                },
                ...
            ]
        """
        if not self.is_connected:
            return []

        try:
            result = self.client.table(self.TABLE_MAPPINGS).select("bread_name, bag_name").execute()

            if not result.data:
                return []

            return result.data

        except Exception as e:
            logger.error(f"Failed to get product mappings: {e}")
            return []

    def add_product_mapping(self, bread_name: str, bag_name: str) -> bool:
        """
        Add a new product mapping.

        Args:
            bread_name: Name of the bread product
            bag_name: Name of the corresponding bag

        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected:
            return False

        try:
            self.client.table(self.TABLE_MAPPINGS).upsert({"bread_name": bread_name, "bag_name": bag_name, "updated_at": datetime.now().isoformat()}).execute()
            return True

        except Exception as e:
            logger.error(f"Failed to add product mapping: {e}")
            return False

    def delete_product_mapping(self, bread_name: str, bag_name: str) -> bool:
        """
        Delete a product mapping.

        Args:
            bread_name: Name of the bread product
            bag_name: Name of the corresponding bag

        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected:
            return False

        try:
            self.client.table(self.TABLE_MAPPINGS).delete().eq("bread_name", bread_name).eq("bag_name", bag_name).execute()
            return True

        except Exception as e:
            logger.error(f"Failed to delete product mapping: {e}")
            return False

    def get_inventory_diagnosis(self) -> Dict:
        """
        Get comprehensive inventory diagnosis with all calculations done server-side.

        Returns:
            {
                "snapshot_date": "2025-12-27",
                "bread_items": [...],
                "box_items": [...],
                "bag_items": [...],
                "summary": {
                    "critical_count": 2,
                    "healthy_count": 10,
                    "overstock_count": 3
                }
            }
        """
        if not self.is_connected:
            return {}

        try:
            from datetime import timedelta

            # Constants
            LEAD_TIME = {"bread": 20, "box": 20, "bag": 30}
            TARGET_DAYS = 30

            # 1. Get latest inventory items
            latest_snapshot = self.get_latest_snapshot()
            if not latest_snapshot:
                return {}

            snapshot_id = latest_snapshot.get("id")
            snapshot_date = latest_snapshot.get("snapshot_date", "")[:10]

            # Get all inventory items
            items_result = self.client.table(self.TABLE_ITEMS).select("*").eq("snapshot_id", snapshot_id).execute()

            if not items_result.data:
                return {}

            # 2. Get sales data (stock_out) for past 30 days
            start_date_30d = (datetime.now() - timedelta(days=30)).date().isoformat()
            start_date_20d = (datetime.now() - timedelta(days=20)).date().isoformat()

            # First, get snapshot IDs and dates within the date range
            snapshots_result = (
                self.client.table(self.TABLE_SNAPSHOTS)
                .select("id, snapshot_date")
                .gte("snapshot_date", start_date_30d)
                .execute()
            )

            if not snapshots_result.data:
                # No snapshots in range, skip sales calculation
                sales_30d: Dict[str, int] = {}
                sales_20d: Dict[str, int] = {}
                latest_sales: Dict[str, Dict] = {}
            else:
                # Create a map of snapshot_id -> date
                snapshot_date_map = {s["id"]: s["snapshot_date"][:10] for s in snapshots_result.data}
                snapshot_ids = list(snapshot_date_map.keys())

                # Query raw items with pagination to get all records (Supabase default limit is 1000)
                all_raw_items = []
                page_size = 1000
                offset = 0

                while True:
                    raw_items_result = (
                        self.client.table(self.TABLE_RAW_ITEMS)
                        .select("product_name, stock_out, snapshot_id")
                        .in_("snapshot_id", snapshot_ids)
                        .range(offset, offset + page_size - 1)
                        .execute()
                    )

                    if not raw_items_result.data:
                        break

                    all_raw_items.extend(raw_items_result.data)

                    if len(raw_items_result.data) < page_size:
                        break

                    offset += page_size

                # Calculate sales totals per product
                sales_30d: Dict[str, int] = {}
                sales_20d: Dict[str, int] = {}
                # Track latest day's stock_out per product (for 日銷 display)
                latest_sales: Dict[str, Dict] = {}  # {product_name: {"date": date_str, "stock_out": int}}

                for row in all_raw_items:
                    name = row["product_name"]
                    stock_out = int(row.get("stock_out", 0) or 0)
                    snapshot_id = row.get("snapshot_id")
                    date_str = snapshot_date_map.get(snapshot_id, "")

                    # Add to 30-day total
                    sales_30d[name] = sales_30d.get(name, 0) + stock_out

                    # Add to 20-day total if within range
                    if date_str and date_str >= start_date_20d:
                        sales_20d[name] = sales_20d.get(name, 0) + stock_out

                    # Track latest day's stock_out (accumulate if same day)
                    if date_str:
                        if name not in latest_sales:
                            latest_sales[name] = {"date": date_str, "stock_out": stock_out}
                        elif date_str > latest_sales[name]["date"]:
                            # New latest date, reset
                            latest_sales[name] = {"date": date_str, "stock_out": stock_out}
                        elif date_str == latest_sales[name]["date"]:
                            # Same day, accumulate stock_out
                            latest_sales[name]["stock_out"] += stock_out

            # 3. Get product mappings (bread to bag)
            mappings = self.get_product_mappings()
            bread_to_bag = {m["bread_name"]: m["bag_name"] for m in mappings}
            bag_to_bread = {m["bag_name"]: m["bread_name"] for m in mappings}

            # Constants for bag calculation
            BAG_CAPACITY = 6000  # 一卷塑膠袋可包 6000 個麵包

            # 4. Build diagnosis for each item
            def calculate_diagnosis(item: Dict, category: str) -> Dict:
                name = item["name"]
                current_stock = int(item.get("available_stock", 0) or item.get("current_stock", 0))
                unit = item.get("unit", "個")

                # Sales calculations
                total_30d = sales_30d.get(name, 0)
                total_20d = sales_20d.get(name, 0)
                daily_30d = round(total_30d / 30) if total_30d > 0 else 0
                daily_20d = round(total_20d / 20) if total_20d > 0 else 0

                # Get latest day's stock_out for 日銷 display
                latest_daily = latest_sales.get(name, {}).get("stock_out", 0)

                # Stock metrics using new formulas:
                # 正常水位 = 最近30日銷量總和
                # 補貨點 = 30日均銷量 × 20
                # 可售天數 = 目前庫存 / 30日均銷量
                if daily_30d > 0:
                    days_of_stock = round(current_stock / daily_30d, 1)
                    reorder_point = daily_30d * 20  # 30日均銷量 × 20
                    target_stock = total_30d  # 30日銷量總量作為正常水位

                    # Health status
                    if current_stock < reorder_point:
                        health_status = "critical"
                    elif current_stock > total_30d:
                        health_status = "overstock"
                    else:
                        health_status = "healthy"

                    # Suggested order (補到正常水位)
                    suggested_order = max(0, target_stock - current_stock) if health_status == "critical" else 0
                else:
                    days_of_stock = 999
                    reorder_point = 0
                    target_stock = 0
                    health_status = "healthy"  # No sales data, default healthy
                    suggested_order = 0

                return {
                    "name": name,
                    "category": category,
                    "current_stock": current_stock,
                    "unit": unit,
                    "daily_sales": latest_daily,  # 日銷：最新一天的出庫量
                    "daily_sales_30d": daily_30d,  # 30日均銷量
                    "daily_sales_20d": daily_20d,
                    "total_sales_30d": total_30d,
                    "total_sales_20d": total_20d,
                    "days_of_stock": days_of_stock,  # 可售天數 = 目前庫存 / 30日均銷量
                    "reorder_point": round(reorder_point),  # 補貨點 = 30日均銷量 × 20
                    "target_stock": round(target_stock),  # 正常水位 = 30日銷量總和
                    "health_status": health_status,
                    "suggested_order": round(suggested_order),
                }

            # Process items by category
            bread_items = []
            box_items = []
            bag_items = []

            # Create a lookup for bag diagnoses
            bag_lookup: Dict[str, Dict] = {}

            # Track which bags we've seen in current inventory
            bags_in_inventory: set = set()

            # Store raw bag items for later processing (after bread items are ready)
            raw_bag_items = []

            for item in items_result.data:
                category = item.get("category", "other")
                if category == "bread":
                    diagnosis = calculate_diagnosis(item, "bread")
                    bread_items.append(diagnosis)
                elif category == "box":
                    diagnosis = calculate_diagnosis(item, "box")
                    box_items.append(diagnosis)
                elif category == "bag":
                    # Store for later processing
                    raw_bag_items.append(item)
                    bags_in_inventory.add(item["name"])

            # Create bread lookup for bag calculations
            bread_lookup = {b["name"]: b for b in bread_items}

            # 5. Calculate bag diagnosis based on corresponding bread
            import math

            def calculate_bag_diagnosis(bag_name: str, current_stock: int) -> Dict:
                """
                Calculate bag reorder_point and target_stock based on corresponding bread.
                一卷塑膠袋可包 6000 個麵包，根據麵包的補貨點計算塑膠袋需求量，無條件進位
                """
                lead_time = LEAD_TIME.get("bag", 30)

                # Find corresponding bread
                bread_name = bag_to_bread.get(bag_name)
                if bread_name and bread_name in bread_lookup:
                    bread = bread_lookup[bread_name]
                    bread_reorder_point = bread.get("reorder_point", 0)

                    # 塑膠袋補貨點 = 麵包補貨點 / 6000，無條件進位
                    if bread_reorder_point > 0:
                        bag_reorder_point = math.ceil(bread_reorder_point / BAG_CAPACITY)
                    else:
                        bag_reorder_point = 0

                    # 正常水位 = 補貨點
                    bag_target_stock = bag_reorder_point

                    # Health status based on bag stock vs reorder point
                    if bag_reorder_point > 0:
                        if current_stock < bag_reorder_point:
                            health_status = "critical"
                        elif current_stock > bag_target_stock * 2:
                            health_status = "overstock"
                        else:
                            health_status = "healthy"
                    else:
                        health_status = "healthy"

                    # Suggested order
                    suggested_order = max(0, bag_target_stock - current_stock) if health_status == "critical" else 0
                else:
                    # No corresponding bread found
                    bag_reorder_point = 0
                    bag_target_stock = 0
                    health_status = "healthy" if current_stock > 0 else "critical"
                    suggested_order = 0

                return {
                    "name": bag_name,
                    "category": "bag",
                    "current_stock": current_stock,
                    "unit": "捲",
                    "lead_time": lead_time,
                    "reorder_point": bag_reorder_point,
                    "target_stock": bag_target_stock,
                    "health_status": health_status,
                    "suggested_order": suggested_order,
                }

            # Process raw bag items
            for item in raw_bag_items:
                bag_name = item["name"]
                current_stock = int(item.get("available_stock", 0) or item.get("current_stock", 0))
                diagnosis = calculate_bag_diagnosis(bag_name, current_stock)
                bag_items.append(diagnosis)
                bag_lookup[bag_name] = diagnosis

            # Add missing bags from master_bags (庫存為0的塑膠袋)
            master_bags = self.get_master_bags()
            for master_bag in master_bags:
                bag_name = master_bag.get("name")
                if bag_name and bag_name not in bags_in_inventory:
                    # Create diagnosis for zero-stock bags
                    diagnosis = calculate_bag_diagnosis(bag_name, 0)
                    bag_items.append(diagnosis)
                    bag_lookup[bag_name] = diagnosis

            # 6. Match bags to breads
            for bread in bread_items:
                bag_name = bread_to_bag.get(bread["name"])
                if bag_name and bag_name in bag_lookup:
                    bread["matched_bag"] = bag_lookup[bag_name]
                else:
                    # Try fallback matching
                    for bag in bag_items:
                        bag_base = bag["name"].replace("塑膠袋-", "").replace("塑膠袋", "")
                        if bag_base == bread["name"] or bread["name"].endswith(bag_base):
                            bread["matched_bag"] = bag
                            break
                    else:
                        bread["matched_bag"] = None

            # 7. Calculate summary
            all_items = bread_items + box_items + bag_items
            total_bag_rolls = sum(i["current_stock"] for i in bag_items)
            summary = {
                "critical_count": len([i for i in all_items if i["health_status"] == "critical"]),
                "healthy_count": len([i for i in all_items if i["health_status"] == "healthy"]),
                "overstock_count": len([i for i in all_items if i["health_status"] == "overstock"]),
                "total_bread_stock": sum(i["current_stock"] for i in bread_items),
                "total_box_stock": sum(i["current_stock"] for i in box_items),
                "total_bag_stock": total_bag_rolls,
                "total_bag_capacity": total_bag_rolls * BAG_CAPACITY,  # 可包裝量 = 塑膠袋卷數 * 6000
            }

            return {
                "snapshot_date": snapshot_date,
                "bread_items": bread_items,
                "box_items": box_items,
                "bag_items": bag_items,
                "summary": summary,
            }

        except Exception as e:
            logger.error(f"Failed to get inventory diagnosis: {e}")
            return {}

    # =============================================
    # Master Data Management
    # =============================================

    def get_master_breads(self) -> List[Dict]:
        """Get all bread master records."""
        if not self.is_connected:
            return []
        try:
            result = self.client.table(self.TABLE_MASTER_BREADS).select("*").order("name").execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Failed to get master breads: {e}")
            return []

    def get_master_bags(self) -> List[Dict]:
        """Get all bag master records."""
        if not self.is_connected:
            return []
        try:
            result = self.client.table(self.TABLE_MASTER_BAGS).select("*").order("name").execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Failed to get master bags: {e}")
            return []

    def get_master_boxes(self) -> List[Dict]:
        """Get all box master records."""
        if not self.is_connected:
            return []
        try:
            result = self.client.table(self.TABLE_MASTER_BOXES).select("*").order("name").execute()
            return result.data or []
        except Exception as e:
            logger.error(f"Failed to get master boxes: {e}")
            return []

    def add_master_bread(self, name: str, code: str = None) -> bool:
        """Add a bread to master records."""
        if not self.is_connected:
            return False
        try:
            data = {"name": name, "updated_at": datetime.now().isoformat()}
            if code:
                data["code"] = code
            self.client.table(self.TABLE_MASTER_BREADS).upsert(data).execute()
            return True
        except Exception as e:
            logger.error(f"Failed to add master bread: {e}")
            return False

    def add_master_bag(self, name: str, code: str = None) -> bool:
        """Add a bag to master records."""
        if not self.is_connected:
            return False
        try:
            data = {"name": name, "updated_at": datetime.now().isoformat()}
            if code:
                data["code"] = code
            self.client.table(self.TABLE_MASTER_BAGS).upsert(data).execute()
            return True
        except Exception as e:
            logger.error(f"Failed to add master bag: {e}")
            return False

    def add_master_box(self, name: str, code: str = None) -> bool:
        """Add a box to master records."""
        if not self.is_connected:
            return False
        try:
            data = {"name": name, "updated_at": datetime.now().isoformat()}
            if code:
                data["code"] = code
            self.client.table(self.TABLE_MASTER_BOXES).upsert(data).execute()
            return True
        except Exception as e:
            logger.error(f"Failed to add master box: {e}")
            return False

    def sync_master_data_from_inventory(self) -> Dict[str, int]:
        """
        Sync master data from historical inventory records.

        Returns:
            Dict with counts of synced items per category
        """
        if not self.is_connected:
            return {"breads": 0, "bags": 0, "boxes": 0}

        try:
            # Get unique product names from inventory items
            items_result = self.client.table(self.TABLE_ITEMS).select("name, category").execute()

            if not items_result.data:
                return {"breads": 0, "bags": 0, "boxes": 0}

            # Group by category
            breads = set()
            bags = set()
            boxes = set()

            for item in items_result.data:
                name = item.get("name")
                category = item.get("category")
                if category == "bread":
                    breads.add(name)
                elif category == "bag":
                    bags.add(name)
                elif category == "box":
                    boxes.add(name)

            # Insert into master tables
            for name in breads:
                self.add_master_bread(name)
            for name in bags:
                self.add_master_bag(name)
            for name in boxes:
                self.add_master_box(name)

            return {"breads": len(breads), "bags": len(bags), "boxes": len(boxes)}

        except Exception as e:
            logger.error(f"Failed to sync master data: {e}")
            return {"breads": 0, "bags": 0, "boxes": 0}

    def _auto_sync_master_data(self, snapshot: "InventorySnapshot") -> Dict[str, int]:
        """
        Auto-sync new items from snapshot to master tables.
        Called automatically when saving a new snapshot.

        This ensures that when new products appear in vendor Excel files,
        they are automatically added to master_breads, master_bags, and master_boxes.

        Args:
            snapshot: The inventory snapshot being saved

        Returns:
            Dict with counts of newly added items per category
        """
        if not self.is_connected:
            return {"breads": 0, "bags": 0, "boxes": 0}

        try:
            # Get existing master data for comparison
            existing_breads = {b["name"] for b in self.get_master_breads()}
            existing_bags = {b["name"] for b in self.get_master_bags()}
            existing_boxes = {b["name"] for b in self.get_master_boxes()}

            new_breads = 0
            new_bags = 0
            new_boxes = 0

            # Check bread items
            for item in snapshot.bread_items:
                if item.name and item.name not in existing_breads:
                    if self.add_master_bread(item.name):
                        new_breads += 1
                        logger.info(f"Auto-added new bread to master: {item.name}")

            # Check bag items
            for item in snapshot.bag_items:
                if item.name and item.name not in existing_bags:
                    if self.add_master_bag(item.name):
                        new_bags += 1
                        logger.info(f"Auto-added new bag to master: {item.name}")

            # Check box items
            for item in snapshot.box_items:
                if item.name and item.name not in existing_boxes:
                    if self.add_master_box(item.name):
                        new_boxes += 1
                        logger.info(f"Auto-added new box to master: {item.name}")

            if new_breads or new_bags or new_boxes:
                logger.success(f"Auto-synced master data: {new_breads} breads, {new_bags} bags, {new_boxes} boxes")

            return {"breads": new_breads, "bags": new_bags, "boxes": new_boxes}

        except Exception as e:
            logger.error(f"Failed to auto-sync master data: {e}")
            return {"breads": 0, "bags": 0, "boxes": 0}

    def get_product_codes_map(self) -> Dict[str, Dict]:
        """
        Get all product codes from product_codes table.

        Returns:
            Dict mapping code to info:
            {
                "bagel101": {"code": "bagel101", "name": "Basic Bagel", "qty": 14},
                ...
            }
        """
        if not self.is_connected:
            return {}

        try:
            # Query all product codes (limit 1000 for now, implementation plan assumes simplified logic)
            result = self.client.table("product_codes").select("*").execute()
            
            if not result.data:
                return {}

            return {item["code"]: item for item in result.data}

        except Exception as e:
            logger.error(f"Failed to get product codes map: {e}")
            return {}

    def get_product_alias_map(self) -> Dict[str, str]:
        """
        Get all product aliases from product_aliases table.

        Returns:
            Dict mapping alias to product_code:
            {
                "減醣貝果14天體驗組": "bagel101-14day",
                ...
            }
        """
        if not self.is_connected:
            return {}

        try:
            # Query all aliases
            # Note: If there are many aliases (>1000), need pagination. 
            # For now assuming <1000 for simplicity as per current config size.
            result = self.client.table("product_aliases").select("alias, product_code").execute()

            if not result.data:
                return {}

            return {item["alias"]: item["product_code"] for item in result.data}

        except Exception as e:
            logger.error(f"Failed to get product alias map: {e}")
            return {}

    # =========================================================================
    # Product Management Methods
    # =========================================================================

    def get_all_products_detailed(self) -> List[Dict]:
        """
        Get all products with aliases.
        """
        if not self.is_connected:
            return []

        try:
            # Fetch products
            products_res = self.client.table("product_codes").select("*").execute()
            products = products_res.data if products_res.data else []
            
            # Fetch aliases
            aliases_res = self.client.table("product_aliases").select("*").execute()
            aliases = aliases_res.data if aliases_res.data else []

            # Group aliases by product_code
            alias_map: Dict[str, List[Dict]] = {}
            for alias in aliases:
                p_code = alias["product_code"]
                if p_code not in alias_map:
                    alias_map[p_code] = []
                alias_map[p_code].append(alias)

            # Combine
            result = []
            for p in products:
                p["aliases"] = alias_map.get(p["code"], [])
                result.append(p)
            
            return result

        except Exception as e:
            logger.error(f"Failed to get detailed products: {e}")
            return []

    def create_product(self, code: str, name: str, qty: int) -> Dict:
        try:
            data = {"code": code, "name": name, "qty": qty}
            res = self.client.table("product_codes").insert(data).execute()
            return res.data[0] if res.data else None
        except Exception as e:
            logger.error(f"Failed to create product: {e}")
            raise e

    def update_product_qty(self, code: str, qty: int) -> Dict:
        try:
            res = self.client.table("product_codes").update({"qty": qty}).eq("code", code).execute()
            return res.data[0] if res.data else None
        except Exception as e:
            logger.error(f"Failed to update product qty: {e}")
            raise e

    def delete_product(self, code: str) -> bool:
        try:
            # Casacde delete aliases first? Supabase usually handles cascade if configured,
            # but manually deleting is safer if not sure about schema FK cleanup.
            self.client.table("product_aliases").delete().eq("product_code", code).execute()
            self.client.table("product_codes").delete().eq("code", code).execute()
            return True
        except Exception as e:
            logger.error(f"Failed to delete product: {e}")
            return False

    def add_product_alias(self, product_code: str, alias: str) -> Dict:
        try:
            data = {"product_code": product_code, "alias": alias}
            res = self.client.table("product_aliases").insert(data).execute()
            return res.data[0] if res.data else None
        except Exception as e:
            logger.error(f"Failed to add alias: {e}")
            raise e

    def delete_product_alias(self, alias_id: int) -> bool:
        try:
            self.client.table("product_aliases").delete().eq("id", alias_id).execute()
            return True
        except Exception as e:
            logger.error(f"Failed to delete alias: {e}")
            return False

    # =========================================================================
    # Column Mapping Methods (Unified - No Platform Separation)
    # =========================================================================

    def get_column_mappings(self) -> Dict[str, List[str]]:
        """
        Get unified column mappings.
        Returns: { 'order_id': ['訂單編號', 'Order ID', ...], ... }
        """
        if not self.is_connected:
            return {}

        try:
            res = self.client.table("column_mappings").select("*").execute()
            data = res.data if res.data else []

            result = {}
            for row in data:
                result[row["field_name"]] = row["aliases"]
            return result
        except Exception as e:
            logger.error(f"Failed to get column mappings: {e}")
            return {}

    def update_column_mappings(self, mappings: Dict[str, List[str]]) -> bool:
        """
        Update all column mappings (full replacement).
        """
        if not self.is_connected:
            return False

        try:
            # Upsert each field
            for field_name, aliases in mappings.items():
                data = {
                    "field_name": field_name,
                    "aliases": aliases,
                    "updated_at": "now()"
                }
                self.client.table("column_mappings").upsert(data, on_conflict="field_name").execute()
            return True
        except Exception as e:
            logger.error(f"Failed to update column mappings: {e}")
            return False

    def update_field_aliases(self, field_name: str, aliases: List[str]) -> bool:
        """
        Update aliases for a single field.
        """
        if not self.is_connected:
            return False

        try:
            data = {
                "field_name": field_name,
                "aliases": aliases,
                "updated_at": "now()"
            }
            self.client.table("column_mappings").upsert(data, on_conflict="field_name").execute()
            return True
        except Exception as e:
            logger.error(f"Failed to update field aliases: {e}")
            return False

    # ============================================================
    # Sales Methods (銷量相關方法)
    # ============================================================

    def get_master_sales_products(self) -> List[Dict]:
        """
        取得所有銷量商品主檔

        Returns:
            商品列表
        """
        try:
            result = self.client.table(self.TABLE_MASTER_SALES_PRODUCTS).select("*").order("product_name").execute()
            return result.data
        except Exception as e:
            logger.error(f"Failed to get master sales products: {e}")
            return []

    def upsert_master_sales_products(self, products: List[Dict]) -> bool:
        """
        批次新增/更新銷量商品主檔

        Args:
            products: 商品列表，格式：
                [
                    {
                        "product_name": "商品名稱",
                        "category": "bread" or "box",
                        "first_seen_date": "2026-01-08",
                        "last_seen_date": "2026-01-08",
                        "is_active": True
                    }
                ]

        Returns:
            True if successful
        """
        try:
            # 使用 upsert，on_conflict 為 product_name
            self.client.table(self.TABLE_MASTER_SALES_PRODUCTS).upsert(
                products,
                on_conflict="product_name"
            ).execute()

            logger.success(f"Upserted {len(products)} products to master_sales_products")
            return True
        except Exception as e:
            logger.error(f"Failed to upsert master sales products: {e}")
            return False

    def save_daily_sales_batch(self, records: List[Dict]) -> bool:
        """
        批次儲存每日銷量記錄

        Args:
            records: 銷量記錄列表，格式：
                [
                    {
                        "sale_date": "2026-01-08",
                        "product_name": "商品名稱",
                        "category": "bread" or "box",
                        "quantity": 100,
                        "source": "flowtide_qc"
                    }
                ]

        Returns:
            True if successful
        """
        try:
            # 使用 upsert，on_conflict 為 (sale_date, product_name)
            # Supabase 會自動處理 UNIQUE constraint
            self.client.table(self.TABLE_DAILY_SALES).upsert(
                records,
                on_conflict="sale_date,product_name"
            ).execute()

            logger.success(f"Saved {len(records)} daily sales records")
            return True
        except Exception as e:
            logger.error(f"Failed to save daily sales: {e}")
            return False

    def get_daily_sales(self, start_date: str, end_date: str = None, category: str = None) -> List[Dict]:
        """
        查詢每日銷量記錄

        Args:
            start_date: 開始日期 (YYYY-MM-DD)
            end_date: 結束日期 (YYYY-MM-DD)，不指定則查到最新
            category: 分類過濾 ("bread" or "box")

        Returns:
            銷量記錄列表
        """
        try:
            query = self.client.table(self.TABLE_DAILY_SALES).select("*").gte("sale_date", start_date)

            if end_date:
                query = query.lte("sale_date", end_date)

            if category:
                query = query.eq("category", category)

            result = query.order("sale_date", desc=True).execute()
            return result.data
        except Exception as e:
            logger.error(f"Failed to get daily sales: {e}")
            return []

    def get_sales_summary(self, days: int = 30) -> Dict:
        """
        取得銷量摘要統計

        Args:
            days: 統計天數

        Returns:
            摘要資料：
            {
                "total_sales": 總銷量,
                "by_category": {"bread": xxx, "box": xxx},
                "top_products": [...]
            }
        """
        try:
            from datetime import datetime, timedelta

            # 計算日期範圍
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            # 查詢銷量資料
            records = self.get_daily_sales(
                start_date.strftime("%Y-%m-%d"),
                end_date.strftime("%Y-%m-%d")
            )

            if not records:
                return {"total_sales": 0, "by_category": {}, "top_products": []}

            # 彙總統計
            total_sales = 0
            by_category = {}
            by_product = {}

            for record in records:
                quantity = record.get("quantity", 0)
                category = record.get("category", "unknown")
                product_name = record.get("product_name", "")

                total_sales += quantity

                if category not in by_category:
                    by_category[category] = 0
                by_category[category] += quantity

                if product_name not in by_product:
                    by_product[product_name] = 0
                by_product[product_name] += quantity

            # 排序取前10名
            top_products = sorted(
                [{"product_name": k, "quantity": v} for k, v in by_product.items()],
                key=lambda x: x["quantity"],
                reverse=True
            )[:10]

            return {
                "total_sales": total_sales,
                "by_category": by_category,
                "top_products": top_products
            }

        except Exception as e:
            logger.error(f"Failed to get sales summary: {e}")
            return {"total_sales": 0, "by_category": {}, "top_products": []}

