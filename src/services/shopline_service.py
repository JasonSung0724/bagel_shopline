"""
ShopLine order service for order status management.
"""
import json
from typing import Dict, List, Optional, Tuple
from loguru import logger

from src.repositories.shopline_repository import ShopLineRepository
from src.repositories.tcat_repository import TcatRepository
from src.config.config import ConfigManager


class ShopLineService:
    """
    Service for ShopLine order management.
    """

    # Status mapping: Tcat status -> ShopLine delivery status
    STATUS_MAP = {
        "arrived": ["順利送達"],
        "shipped": ["已集貨"],
        "returning": ["取消取件"],
        "returned": ["退貨完成"],
    }

    def __init__(self):
        """Initialize ShopLine service."""
        self.shopline_repo = ShopLineRepository()
        self.tcat_repo = TcatRepository()
        self.config = ConfigManager()

    def map_tcat_to_shopline_status(self, tcat_status: str) -> Optional[str]:
        """
        Map Tcat status to ShopLine delivery status.

        Args:
            tcat_status: Tcat status string

        Returns:
            ShopLine delivery status or None
        """
        for shopline_status, tcat_statuses in self.STATUS_MAP.items():
            if tcat_status in tcat_statuses:
                return shopline_status
        return None

    def process_email_orders(
        self,
        orders: List[Dict],
        notify: bool = False
    ) -> Tuple[int, int]:
        """
        Process orders from email attachments.

        Args:
            orders: List of order dicts from email
            notify: Whether to send email notifications

        Returns:
            Tuple of (tracking_updated_count, status_updated_count)
        """
        tracking_count = 0
        status_count = 0

        for order in orders:
            order_number = order.get("order_number")
            tcat_number = order.get("tcat_number")

            if not order_number or not tcat_number:
                continue

            # Get order from ShopLine
            order_detail = self.shopline_repo.query_order_by_number(order_number)
            if not order_detail:
                logger.warning(f"找不到訂單 {order_number}")
                continue

            # Check if custom delivery
            if not self.shopline_repo.is_custom_delivery(order_detail):
                continue

            order_id = order_detail.get("id")
            current_tracking = self.shopline_repo.get_tracking_number(order_detail)
            current_status = self.shopline_repo.get_delivery_status(order_detail)

            # Update tracking info if not set
            if not current_tracking:
                tracking_url = self.tcat_repo.get_tracking_url(tcat_number)
                if self.shopline_repo.update_tracking_info(
                    order_id, tcat_number, tracking_url
                ):
                    tracking_count += 1
                    logger.info(f"更新 {order_number} 追蹤資訊")

            # Get Tcat status and update if needed
            tcat_status = self.tcat_repo.get_order_status(tcat_number)
            updated = self._update_order_status(
                order_id, order_number, tcat_status, current_status, notify
            )
            if updated:
                status_count += 1

        logger.success(f"更新追蹤資訊 {tracking_count} 筆, 更新狀態 {status_count} 筆")
        return tracking_count, status_count

    def process_outstanding_orders(self, notify: bool = False) -> int:
        """
        Process all outstanding orders.

        Args:
            notify: Whether to send email notifications

        Returns:
            Number of orders updated
        """
        orders = self.shopline_repo.get_all_outstanding_orders()
        update_count = 0

        for order in orders:
            tracking_number = self.shopline_repo.get_tracking_number(order)
            if not tracking_number:
                order_num = order.get("order_number", "unknown")
                logger.warning(f"訂單 {order_num} 沒有追蹤號")
                continue

            order_id = order.get("id")
            order_number = order.get("order_number")
            current_status = self.shopline_repo.get_delivery_status(order)

            # Query Tcat status
            tcat_status = self.tcat_repo.get_order_status(tracking_number)

            # Update if needed
            updated = self._update_order_status(
                order_id, order_number, tcat_status, current_status, notify
            )
            if updated:
                update_count += 1

        logger.success(f"更新 {update_count} 筆訂單狀態")
        return update_count

    def _update_order_status(
        self,
        order_id: str,
        order_number: str,
        tcat_status: str,
        current_delivery_status: str,
        notify: bool = False
    ) -> bool:
        """
        Update order status based on Tcat status.

        Args:
            order_id: ShopLine order ID
            order_number: Order number for logging
            tcat_status: Current Tcat status
            current_delivery_status: Current ShopLine delivery status
            notify: Whether to send notifications

        Returns:
            True if status was updated
        """
        # Map to ShopLine status
        new_delivery_status = self.map_tcat_to_shopline_status(tcat_status)
        if not new_delivery_status:
            return False

        # Skip if same status
        if current_delivery_status == new_delivery_status:
            return False

        # Update delivery status
        if not self.shopline_repo.update_delivery_status(
            order_id, new_delivery_status, notify
        ):
            logger.error(f"更新 {order_number} 配送狀態失敗")
            return False

        logger.info(f"更新 {order_number} 配送狀態: {current_delivery_status} -> {new_delivery_status}")

        # Handle special cases
        if new_delivery_status == "arrived":
            self.shopline_repo.update_order_status(order_id, "completed", notify)
            logger.info(f"訂單 {order_number} 已完成")

        elif new_delivery_status == "returned":
            self.shopline_repo.update_order_status(order_id, "cancelled", notify)
            logger.info(f"訂單 {order_number} 已取消（退貨）")

        return True

    def get_order_status(self, order_number: str) -> Optional[Dict]:
        """
        Get order status from ShopLine.

        Args:
            order_number: Order number

        Returns:
            Order status dict or None
        """
        order = self.shopline_repo.query_order_by_number(order_number)
        if not order:
            return None

        return {
            "order_id": order.get("id"),
            "order_number": order.get("order_number"),
            "delivery_status": self.shopline_repo.get_delivery_status(order),
            "tracking_number": self.shopline_repo.get_tracking_number(order),
            "order_status": order.get("status"),
        }
