"""
Inventory data models.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum


class InventoryCategory(Enum):
    """Inventory item category."""
    BREAD = "bread"      # 麵包/貝果
    BOX = "box"          # 盒子/紙箱
    BAG = "bag"          # 袋子
    OTHER = "other"      # 其他


# Excel 欄位對應表 (中文 -> 英文)
EXCEL_COLUMN_MAPPING = {
    "品名": "product_name",
    "主檔規格": "spec",
    "主檔箱入數": "box_quantity",
    "效期": "expiry_date",
    "入倉日期": "warehouse_date",
    "單位": "unit",
    "期初": "opening_stock",
    "入庫": "stock_in",
    "出庫": "stock_out",
    "期末": "closing_stock",
    "未扣帳量": "unbilled_quantity",
    "待出貨量": "pending_shipment",
    "預計可用量": "available_stock",
    "庫別": "warehouse_code",
    "客戶端允收天數": "customer_accept_days",
    "客戶端允收日期": "customer_accept_date",
    "客戶端可收天數": "customer_receivable_days",
    "效期警示": "expiry_warning",
    "初始庫存編號": "initial_stock_id",
    "初始入倉單號": "initial_warehouse_order",
    "初始入倉日期": "initial_warehouse_date",
    "初始入倉數量": "initial_warehouse_quantity",
    "庫存編號": "stock_id",
    "商品批號": "product_batch",
    "儲位": "storage_location",
    "板號": "pallet_number",
    "最後入倉單號": "last_warehouse_order",
    "最後入倉日期": "last_warehouse_date",
    "最後入倉數量": "last_warehouse_quantity",
    "資料日期": "data_date",
}


@dataclass
class InventoryRawItem:
    """
    Raw inventory item from Excel (single row).
    Preserves all original columns for future flexibility.
    """
    # 基本欄位
    product_name: str                          # 品名
    spec: Optional[str] = None                 # 主檔規格
    box_quantity: Optional[int] = None         # 主檔箱入數
    expiry_date: Optional[str] = None          # 效期
    warehouse_date: Optional[str] = None       # 入倉日期
    unit: Optional[str] = None                 # 單位

    # 庫存數量
    opening_stock: float = 0                   # 期初
    stock_in: float = 0                        # 入庫
    stock_out: float = 0                       # 出庫
    closing_stock: float = 0                   # 期末
    unbilled_quantity: float = 0               # 未扣帳量
    pending_shipment: float = 0                # 待出貨量
    available_stock: float = 0                 # 預計可用量

    # 庫別資訊
    warehouse_code: Optional[str] = None       # 庫別

    # 客戶端資訊
    customer_accept_days: Optional[int] = None       # 客戶端允收天數
    customer_accept_date: Optional[str] = None       # 客戶端允收日期
    customer_receivable_days: Optional[int] = None   # 客戶端可收天數
    expiry_warning: Optional[str] = None             # 效期警示

    # 庫存追蹤
    initial_stock_id: Optional[str] = None           # 初始庫存編號
    initial_warehouse_order: Optional[str] = None    # 初始入倉單號
    initial_warehouse_date: Optional[str] = None     # 初始入倉日期
    initial_warehouse_quantity: Optional[float] = None  # 初始入倉數量
    stock_id: Optional[str] = None                   # 庫存編號
    product_batch: Optional[str] = None              # 商品批號

    # 儲位資訊
    storage_location: Optional[str] = None     # 儲位
    pallet_number: Optional[str] = None        # 板號

    # 最後入倉
    last_warehouse_order: Optional[str] = None       # 最後入倉單號
    last_warehouse_date: Optional[str] = None        # 最後入倉日期
    last_warehouse_quantity: Optional[float] = None  # 最後入倉數量

    # 資料日期
    data_date: Optional[str] = None            # 資料日期

    # 系統欄位
    row_number: Optional[int] = None           # Excel 原始列號
    raw_data: Optional[Dict[str, Any]] = None  # 完整原始資料 (JSONB)

    def to_dict(self) -> dict:
        """Convert to dictionary for database insert."""
        return {
            "product_name": self.product_name,
            "spec": self.spec,
            "box_quantity": self.box_quantity,
            "expiry_date": self.expiry_date,
            "warehouse_date": self.warehouse_date,
            "unit": self.unit,
            "opening_stock": self.opening_stock,
            "stock_in": self.stock_in,
            "stock_out": self.stock_out,
            "closing_stock": self.closing_stock,
            "unbilled_quantity": self.unbilled_quantity,
            "pending_shipment": self.pending_shipment,
            "available_stock": self.available_stock,
            "warehouse_code": self.warehouse_code,
            "customer_accept_days": self.customer_accept_days,
            "customer_accept_date": self.customer_accept_date,
            "customer_receivable_days": self.customer_receivable_days,
            "expiry_warning": self.expiry_warning,
            "initial_stock_id": self.initial_stock_id,
            "initial_warehouse_order": self.initial_warehouse_order,
            "initial_warehouse_date": self.initial_warehouse_date,
            "initial_warehouse_quantity": self.initial_warehouse_quantity,
            "stock_id": self.stock_id,
            "product_batch": self.product_batch,
            "storage_location": self.storage_location,
            "pallet_number": self.pallet_number,
            "last_warehouse_order": self.last_warehouse_order,
            "last_warehouse_date": self.last_warehouse_date,
            "last_warehouse_quantity": self.last_warehouse_quantity,
            "data_date": self.data_date,
            "row_number": self.row_number,
            "raw_data": self.raw_data,
        }

    @classmethod
    def from_excel_row(cls, row: dict, row_number: int = 0) -> 'InventoryRawItem':
        """Create from Excel row dictionary."""
        def safe_str(val) -> Optional[str]:
            if val is None or (isinstance(val, float) and str(val) == 'nan'):
                return None
            return str(val).strip() if val else None

        def safe_int(val) -> Optional[int]:
            if val is None or (isinstance(val, float) and str(val) == 'nan'):
                return None
            try:
                return int(float(val))
            except (ValueError, TypeError):
                return None

        def safe_float(val) -> float:
            if val is None or (isinstance(val, float) and str(val) == 'nan'):
                return 0.0
            try:
                return float(val)
            except (ValueError, TypeError):
                return 0.0

        return cls(
            product_name=safe_str(row.get("品名")) or "",
            spec=safe_str(row.get("主檔規格")),
            box_quantity=safe_int(row.get("主檔箱入數")),
            expiry_date=safe_str(row.get("效期")),
            warehouse_date=safe_str(row.get("入倉日期")),
            unit=safe_str(row.get("單位")),
            opening_stock=safe_float(row.get("期初")),
            stock_in=safe_float(row.get("入庫")),
            stock_out=safe_float(row.get("出庫")),
            closing_stock=safe_float(row.get("期末")),
            unbilled_quantity=safe_float(row.get("未扣帳量")),
            pending_shipment=safe_float(row.get("待出貨量")),
            available_stock=safe_float(row.get("預計可用量")),
            warehouse_code=safe_str(row.get("庫別")),
            customer_accept_days=safe_int(row.get("客戶端允收天數")),
            customer_accept_date=safe_str(row.get("客戶端允收日期")),
            customer_receivable_days=safe_int(row.get("客戶端可收天數")),
            expiry_warning=safe_str(row.get("效期警示")),
            initial_stock_id=safe_str(row.get("初始庫存編號")),
            initial_warehouse_order=safe_str(row.get("初始入倉單號")),
            initial_warehouse_date=safe_str(row.get("初始入倉日期")),
            initial_warehouse_quantity=safe_float(row.get("初始入倉數量")) or None,
            stock_id=safe_str(row.get("庫存編號")),
            product_batch=safe_str(row.get("商品批號")),
            storage_location=safe_str(row.get("儲位")),
            pallet_number=safe_str(row.get("板號")),
            last_warehouse_order=safe_str(row.get("最後入倉單號")),
            last_warehouse_date=safe_str(row.get("最後入倉日期")),
            last_warehouse_quantity=safe_float(row.get("最後入倉數量")) or None,
            data_date=safe_str(row.get("資料日期")),
            row_number=row_number,
            raw_data=row,  # 保留完整原始資料
        )


@dataclass
class InventoryItem:
    """
    Single inventory item from Excel.
    Represents aggregated stock for a product.
    """
    name: str                          # 品名
    category: InventoryCategory        # 分類
    current_stock: int                 # 期末庫存 (加總)
    available_stock: int               # 預計可用量 (加總)
    unit: str                          # 單位 (顆/個/捲)
    min_stock: int = 0                 # 最低庫存警戒值

    # For bags (以捲計算)
    items_per_roll: Optional[int] = None  # 每捲數量

    def __post_init__(self):
        """Set default min_stock based on category."""
        if self.min_stock == 0:
            if self.category == InventoryCategory.BREAD:
                self.min_stock = 500  # 麵包最低 500 顆
            elif self.category == InventoryCategory.BOX:
                self.min_stock = 50   # 盒子最低 50 個
            elif self.category == InventoryCategory.BAG:
                self.min_stock = 3    # 袋子最低 3 捲

    @property
    def stock_status(self) -> str:
        """Get stock status: high, medium, low."""
        ratio = self.current_stock / self.min_stock if self.min_stock > 0 else float('inf')
        if ratio >= 2:
            return "high"
        elif ratio >= 1:
            return "medium"
        else:
            return "low"

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "name": self.name,
            "category": self.category.value,
            "current_stock": self.current_stock,
            "available_stock": self.available_stock,
            "unit": self.unit,
            "min_stock": self.min_stock,
            "items_per_roll": self.items_per_roll,
            "stock_status": self.stock_status,
        }


@dataclass
class InventorySnapshot:
    """
    A snapshot of inventory at a specific time.
    Stored in database for historical tracking.
    """
    id: Optional[str] = None
    snapshot_date: datetime = field(default_factory=datetime.now)
    source_file: str = ""              # 來源檔案名稱
    source_email_date: Optional[datetime] = None  # Email 日期

    # 彙總後的項目 (按品名)
    bread_items: List[InventoryItem] = field(default_factory=list)
    box_items: List[InventoryItem] = field(default_factory=list)
    bag_items: List[InventoryItem] = field(default_factory=list)

    # 原始資料 (每一列)
    raw_items: List[InventoryRawItem] = field(default_factory=list)

    @property
    def total_bread_stock(self) -> int:
        """Total bread stock."""
        return sum(item.current_stock for item in self.bread_items)

    @property
    def total_box_stock(self) -> int:
        """Total box stock."""
        return sum(item.current_stock for item in self.box_items)

    @property
    def total_bag_rolls(self) -> int:
        """Total bag rolls."""
        return sum(item.current_stock for item in self.bag_items)

    @property
    def low_stock_count(self) -> int:
        """Count of items with low stock."""
        all_items = self.bread_items + self.box_items + self.bag_items
        return sum(1 for item in all_items if item.stock_status == "low")

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "id": self.id,
            "snapshot_date": self.snapshot_date.isoformat() if self.snapshot_date else None,
            "source_file": self.source_file,
            "source_email_date": self.source_email_date.isoformat() if self.source_email_date else None,
            "summary": {
                "total_bread_stock": self.total_bread_stock,
                "total_box_stock": self.total_box_stock,
                "total_bag_rolls": self.total_bag_rolls,
                "low_stock_count": self.low_stock_count,
            },
            "bread_items": [item.to_dict() for item in self.bread_items],
            "box_items": [item.to_dict() for item in self.box_items],
            "bag_items": [item.to_dict() for item in self.bag_items],
        }


@dataclass
class InventoryChange:
    """
    Record of inventory change (for restock logs).
    """
    id: Optional[str] = None
    date: datetime = field(default_factory=datetime.now)
    item_name: str = ""
    category: InventoryCategory = InventoryCategory.BREAD
    previous_stock: int = 0
    new_stock: int = 0
    change_amount: int = 0  # positive = restock, negative = consumption
    source: str = "email"   # email, manual, adjustment

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "id": self.id,
            "date": self.date.isoformat() if self.date else None,
            "item_name": self.item_name,
            "category": self.category.value,
            "previous_stock": self.previous_stock,
            "new_stock": self.new_stock,
            "change_amount": self.change_amount,
            "source": self.source,
        }
