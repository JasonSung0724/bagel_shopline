from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any, Union
from dataclasses import dataclass, field
from datetime import datetime
import pandas as pd
from loguru import logger
import math

from src.services.product_config_service import ProductConfigService
from src.services.platform_config_service import ColumnMappingService, PlatformConfigService
from src.services.store_address_service import StoreAddressService

@dataclass
class StandardOrderItem:
    """Standardized order item structure."""
    order_id: str
    order_date: str
    receiver_name: str
    receiver_phone: str
    receiver_address: str
    delivery_method: str
    product_code: str
    product_name: str
    quantity: int
    order_mark: str
    arrival_time: Union[int, str] = ""  # 1=上午(13點前), 2=下午(14~18), ""=不限時
    source_platform: str = ""
    original_row: Dict = field(default_factory=dict)

class ConversionResult:
    def __init__(self, items: List[StandardOrderItem], errors: List[Dict]):
        self.items = items
        self.errors = errors

class BaseAdapter(ABC):
    def __init__(self, platform_name: str, product_service: ProductConfigService, config_service: ColumnMappingService):
        self.platform_name = platform_name
        self.product_service = product_service
        self.config_service = config_service
        self.errors = []

        # Load unified mapping (no longer platform-specific)
        self.mapping = self.config_service.get_mapping()

    def add_error(self, order_id: str, field: str, message: str, severity: str = "warning"):
        self.errors.append({
            "order_id": order_id,
            "field": field,
            "message": message,
            "severity": severity
        })

    def get_col_val(self, row: pd.Series, internal_field: str, default: str = "") -> str:
        """
        Smart Search: Get value from row using configured aliases.
        """
        aliases = self.mapping.get(internal_field, [])
        
        for alias in aliases:
            if alias in row and pd.notna(row[alias]):
                val = str(row[alias]).strip()
                if val and val.lower() != 'nan':
                    return val
        return default

    def convert(self, df: pd.DataFrame, store_address_service: Optional[StoreAddressService] = None) -> ConversionResult:
        """
        Template Method: Shared conversion loop.
        """
        items = []
        self.errors = []
        
        # Optional: Store Service Injection hook
        self._prepare_conversion(df, store_address_service)

        for _, row in df.iterrows():
            if self._should_skip(row):
                continue

            extracted = self._process_row(row)
            items.extend(extracted)
            
        return ConversionResult(items, self.errors)

    def _prepare_conversion(self, df: pd.DataFrame, store_address_service: Optional[StoreAddressService]):
        """Hook for pre-processing (like bulk address fetching). Override in subclass."""
        pass

    def _should_skip(self, row: pd.Series) -> bool:
        """Hook to skip rows (e.g. empty ID)."""
        return False

    @abstractmethod
    def _process_row(self, row: pd.Series) -> List[StandardOrderItem]:
        """core logic to process a single row into 1 or more items."""
        pass

    def _create_item(self, **kwargs) -> StandardOrderItem:
        return StandardOrderItem(source_platform=self.platform_name, **kwargs)

    def _format_date(self, date_val: Any) -> str:
        """Format date to YYYYMMDD."""
        if pd.isna(date_val):
            return ""
        try:
            val_str = str(date_val)
            # Try specific common formats
            for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S"]:
                try:
                    dt = datetime.strptime(val_str[:19], fmt) # Trim micros if any
                    return dt.strftime("%Y%m%d")
                except:
                    pass
            
            # If standard pandas timestamp
            if isinstance(date_val, datetime):
                return date_val.strftime("%Y%m%d")
                
        except:
            pass
        return str(date_val).split(" ")[0].replace("-", "").replace("/", "")

# =============================================================================
# Subclasses
# =============================================================================

class ShoplineAdapter(BaseAdapter):
    # Platform prefix for order remarks
    ORDER_MARK_PREFIX = "減醣市集"
    ORDER_MARK_SEPARATOR = "/"

    def __init__(self, product_service: ProductConfigService, config_service: PlatformConfigService):
        super().__init__("Shopline", product_service, config_service)
        self.addresses = {"SEVEN": {}, "FAMILY": {}}

    def _prepare_conversion(self, df: pd.DataFrame, store_address_service: Optional[StoreAddressService]):
        if store_address_service:
            seven_stores = []
            family_stores = []
            for _, row in df.iterrows():
                delivery = self.get_col_val(row, "delivery_method")
                store = self.get_col_val(row, "store_name")
                if "7-11" in delivery and store: seven_stores.append(store)
                elif "全家" in delivery and store: family_stores.append(store)
            
            self.addresses = store_address_service.fetch_store_addresses(list(set(seven_stores)), list(set(family_stores)))

    def _should_skip(self, row: pd.Series) -> bool:
        # Skip if no product code (parent bundle item)
        product_code = self.get_col_val(row, "product_code")
        if not product_code:
            # Debug: log first skip to help diagnose mapping issues
            if not hasattr(self, '_skip_logged'):
                self._skip_logged = True
                logger.debug(f"Skipping row - no product_code found. Aliases: {self.mapping.get('product_code', [])}. Columns: {list(row.index)[:5]}...")
        return not product_code

    def _process_row(self, row: pd.Series) -> List[StandardOrderItem]:
        order_id = self.get_col_val(row, "order_id")
        product_code = self.get_col_val(row, "product_code")
        
        # Address Logic
        delivery_raw = self.get_col_val(row, "delivery_method")
        delivery_simple = delivery_raw.split("（")[0] if "（" in delivery_raw else delivery_raw
        store_name = self.get_col_val(row, "store_name")
        full_address = self.get_col_val(row, "receiver_address")

        if not full_address:
             logger.warning(f"Empty address for Order {order_id}. Available columns: {list(row.index)}")
             logger.warning(f"Tried aliases for receiver_address: {self.mapping.get('receiver_address')}")
        
        final_address = full_address
        final_delivery = "Tcat"

        if "黑貓" in delivery_simple or "宅配" in delivery_simple:
            final_delivery = "Tcat"
        elif "全家" in delivery_simple:
            final_delivery = "全家"
            addr = self.addresses["FAMILY"].get(store_name)
            if not addr or "ERROR" in addr:
                self.add_error(order_id, "地址", f"找不到全家門市: {store_name}", "error")
                final_address = "ERROR"
            else:
                final_address = f"{store_name} ({addr})"
        elif "7-11" in delivery_simple:
            final_delivery = "7-11"
            addr = self.addresses["SEVEN"].get(store_name)
            if not addr or "ERROR" in addr:
                self.add_error(order_id, "地址", f"找不到7-11門市: {store_name}", "error")
                final_address = "ERROR"
            else:
                final_address = f"(宅轉店){addr}"

        # Product Name
        p_name = self.get_col_val(row, "product_name")
        parts = product_code.split("-")
        suffix = f"-{parts[2]}" if len(parts) >= 3 else ""
        final_product_name = f"{p_name}{suffix}"

        # Qty
        try:
            qty = int(float(self.get_col_val(row, "quantity") or 0))
        except: qty = 0

        # Arrival time: 1 = 上午到貨 (13點前), 2 = 下午到貨 (14~18)
        # Legacy logic: exact match required (not contains)
        arrival = ""
        raw_arrival = self.get_col_val(row, "arrival_time")
        if raw_arrival == "上午到貨":
            arrival = 1
        elif raw_arrival == "下午到貨":
            arrival = 2

        # Format order_mark with platform prefix (like legacy: "減醣市集/備註內容")
        raw_mark = self.get_col_val(row, "order_mark")
        if raw_mark and raw_mark.lower() != "nan":
            formatted_mark = f"{self.ORDER_MARK_PREFIX}{self.ORDER_MARK_SEPARATOR}{raw_mark}"
        else:
            formatted_mark = self.ORDER_MARK_PREFIX

        return [self._create_item(
            order_id=order_id,
            order_date=self._format_date(self.get_col_val(row, "order_date")),
            receiver_name=self.get_col_val(row, "receiver_name"),
            receiver_phone=self.get_col_val(row, "receiver_phone"),
            receiver_address=final_address,
            delivery_method=final_delivery,
            product_code=product_code,
            product_name=final_product_name,
            quantity=qty,
            order_mark=formatted_mark,
            arrival_time=arrival,
            original_row=row.to_dict()
        )]

class MixxAdapter(BaseAdapter):
    # Platform prefix for order remarks
    ORDER_MARK_PREFIX = "減醣市集"
    ORDER_MARK_SEPARATOR = "/"

    def __init__(self, product_service: ProductConfigService, config_service: PlatformConfigService):
        super().__init__("Mixx", product_service, config_service)

    def _process_row(self, row: pd.Series) -> List[StandardOrderItem]:
        p_name_raw = self.get_col_val(row, "product_name")
        p_name_search = p_name_raw.split("｜")[1] if "｜" in p_name_raw else p_name_raw

        product_code = self.product_service.search_product_code(p_name_search) or ""

        try:
             qty = int(float(self.get_col_val(row, "quantity") or 0))
        except: qty = 0

        # Format order_mark with platform prefix (like legacy: "減醣市集/備註內容")
        raw_mark = self.get_col_val(row, "order_mark")
        if raw_mark and raw_mark.lower() != "nan":
            formatted_mark = f"{self.ORDER_MARK_PREFIX}{self.ORDER_MARK_SEPARATOR}{raw_mark}"
        else:
            formatted_mark = self.ORDER_MARK_PREFIX

        return [self._create_item(
            order_id=self.get_col_val(row, "order_id"),
            order_date=datetime.now().strftime("%Y%m%d"),
            receiver_name=self.get_col_val(row, "receiver_name"),
            receiver_phone=self.get_col_val(row, "receiver_phone"),
            receiver_address=self.get_col_val(row, "receiver_address"),
            delivery_method="Tcat",
            product_code=product_code,
            product_name=p_name_search,
            quantity=qty,
            order_mark=formatted_mark,
            original_row=row.to_dict()
        )]

class C2CAdapter(BaseAdapter):
    # Platform prefix for order remarks (C2C has different format)
    ORDER_MARK_PREFIX = "減醣市集 X 快電商 C2C BUY"
    ORDER_MARK_SEPARATOR = " | "

    def __init__(self, product_service: ProductConfigService, config_service: PlatformConfigService):
        super().__init__("C2C", product_service, config_service)

    def _format_order_mark(self, raw_mark: str) -> str:
        """Format order_mark with platform prefix (like legacy: "減醣市集 X 快電商 C2C BUY | 備註內容")"""
        if raw_mark and raw_mark.lower() != "nan":
            return f"{self.ORDER_MARK_PREFIX}{self.ORDER_MARK_SEPARATOR}{raw_mark}"
        return self.ORDER_MARK_PREFIX

    def _process_row(self, row: pd.Series) -> List[StandardOrderItem]:
        raw_code = self.get_col_val(row, "product_code")
        style = self.get_col_val(row, "product_name")

        # Format order_mark once for all items in this row
        formatted_mark = self._format_order_mark(self.get_col_val(row, "order_mark"))

        items = []

        # Special logic for Gift split (F2500000044)
        if raw_code == "F2500000044":
            styles = style.replace("(贈品)-F", "").split("+")
            for i, sub_style in enumerate(styles):
                if i >= 2: break
                found_code = self.product_service.search_product_code(sub_style) or raw_code

                items.append(self._create_item(
                    order_id=self.get_col_val(row, "order_id"),
                    order_date=self._format_date(self.get_col_val(row, "order_date")),
                    receiver_name=self.get_col_val(row, "receiver_name"),
                    receiver_phone=self.get_col_val(row, "receiver_phone"),
                    receiver_address=self.get_col_val(row, "receiver_address"),
                    delivery_method="Tcat",
                    product_code=found_code,
                    product_name=sub_style,
                    quantity=int(float(self.get_col_val(row, "quantity") or 0)),
                    order_mark=formatted_mark,
                    original_row=row.to_dict()
                ))
        else:
            # Normal Logic: Priority Style Lookup > Code Lookup
            found_code = None
            if style:
                found_code = self.product_service.search_product_code(style)

            if not found_code and raw_code:
                found_code = self.product_service.search_product_code(raw_code)

            items.append(self._create_item(
                order_id=self.get_col_val(row, "order_id"),
                order_date=self._format_date(self.get_col_val(row, "order_date")),
                receiver_name=self.get_col_val(row, "receiver_name"),
                receiver_phone=self.get_col_val(row, "receiver_phone"),
                receiver_address=self.get_col_val(row, "receiver_address"),
                delivery_method="Tcat",
                product_code=found_code or raw_code,
                product_name=style,
                quantity=int(float(self.get_col_val(row, "quantity") or 0)),
                order_mark=formatted_mark,
                original_row=row.to_dict()
            ))

        return items

class AoshiAdapter(BaseAdapter):
    # Platform prefix for order remarks (Aoshi has different prefix)
    ORDER_MARK_PREFIX = "減醣市集 X 奧世國際"
    ORDER_MARK_SEPARATOR = "/"

    def __init__(self, product_service: ProductConfigService, config_service: PlatformConfigService):
        super().__init__("Aoshi", product_service, config_service)

    def _process_row(self, row: pd.Series) -> List[StandardOrderItem]:
        p_name = self.get_col_val(row, "product_name")
        found_code = self.product_service.search_product_code(p_name) or ""

        # Format order_mark with platform prefix (like legacy: "減醣市集 X 奧世國際/備註內容")
        raw_mark = self.get_col_val(row, "order_mark")
        if raw_mark and raw_mark.lower() != "nan":
            formatted_mark = f"{self.ORDER_MARK_PREFIX}{self.ORDER_MARK_SEPARATOR}{raw_mark}"
        else:
            formatted_mark = self.ORDER_MARK_PREFIX

        return [self._create_item(
            order_id=self.get_col_val(row, "order_id"),
            order_date=self._format_date(self.get_col_val(row, "order_date")),
            receiver_name=self.get_col_val(row, "receiver_name"),
            receiver_phone=self.get_col_val(row, "receiver_phone"),
            receiver_address=self.get_col_val(row, "receiver_address"),
            delivery_method="Tcat",
            product_code=found_code,
            product_name=p_name,
            quantity=int(float(self.get_col_val(row, "quantity") or 0)),
            order_mark=formatted_mark,
            original_row=row.to_dict()
        )]
