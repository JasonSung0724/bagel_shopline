"""
Order-related data models.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from datetime import datetime


class Platform(Enum):
    """Platform types for orders."""
    C2C = "c2c"
    SHOPLINE = "shopline"


class DeliveryStatus(Enum):
    """Delivery status values for ShopLine."""
    PENDING = "pending"
    SHIPPING = "shipping"
    SHIPPED = "shipped"
    ARRIVED = "arrived"
    COLLECTED = "collected"
    RETURNED = "returned"
    RETURNING = "returning"


class OrderStatus(Enum):
    """Order status values for ShopLine."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TcatStatus(Enum):
    """Tcat delivery status values."""
    COLLECTED = "已集貨"
    DELIVERED = "順利送達"
    NO_DATA = "尚無資料"
    CANCEL_PICKUP = "取消取件"
    RETURNED = "退貨完成"


@dataclass
class Order:
    """
    Represents an order with its delivery information.
    """
    order_number: str
    platform: Platform
    tcat_number: Optional[str] = None
    tcat_status: Optional[str] = None
    shopline_id: Optional[str] = None
    delivery_status: Optional[DeliveryStatus] = None
    order_status: Optional[OrderStatus] = None
    tracking_url: Optional[str] = None
    collected_time: Optional[str] = None
    confirmed_at: Optional[datetime] = None

    def needs_tracking_update(self) -> bool:
        """Check if order needs tracking info to be updated."""
        return self.tcat_number is not None and self.tracking_url is None

    def get_delivery_status_from_tcat(self) -> Optional[DeliveryStatus]:
        """
        Map Tcat status to ShopLine delivery status.

        Returns:
            Mapped DeliveryStatus or None if no mapping exists
        """
        status_map = {
            TcatStatus.COLLECTED.value: DeliveryStatus.SHIPPED,
            TcatStatus.DELIVERED.value: DeliveryStatus.ARRIVED,
            TcatStatus.CANCEL_PICKUP.value: DeliveryStatus.RETURNING,
            TcatStatus.RETURNED.value: DeliveryStatus.RETURNED,
        }
        return status_map.get(self.tcat_status)

    def should_complete_order(self) -> bool:
        """Check if order should be marked as completed."""
        return self.tcat_status == TcatStatus.DELIVERED.value

    def should_cancel_order(self) -> bool:
        """Check if order should be marked as cancelled."""
        return self.tcat_status == TcatStatus.RETURNED.value


@dataclass
class OrderUpdateResult:
    """
    Result of an order update operation.
    """
    order_number: str
    success: bool
    tracking_updated: bool = False
    delivery_status_updated: bool = False
    order_status_updated: bool = False
    error_message: Optional[str] = None
