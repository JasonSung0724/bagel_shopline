"""
Outstanding order workflow orchestrator.
Coordinates the outstanding order status update workflow.
"""

from loguru import logger

from src.services.shopline_service import ShopLineService
from src.services.notification_service import NotificationService


class OutstandingOrderWorkflow:
    """
    Orchestrates the outstanding order update workflow.

    Flow:
    1. Fetch all outstanding orders from ShopLine
    2. Query Tcat status for each order
    3. Update ShopLine order status
    4. Send LINE notification (optional)
    """

    def __init__(self, notify_customers: bool = False, send_line_notification: bool = True):
        """
        Initialize outstanding order workflow.

        Args:
            notify_customers: Whether to send customer notifications for updates
            send_line_notification: Whether to send LINE notification after completion
        """
        self.shopline_service = ShopLineService()
        self.notification = NotificationService()
        self.notify_customers = notify_customers
        self.send_line_notification = send_line_notification

    def run(self) -> bool:
        """
        Run the outstanding order update workflow.

        Returns:
            True if workflow completed successfully
        """
        try:
            logger.info("開始執行待處理訂單更新流程")

            # Process outstanding orders
            update_count = self.shopline_service.process_outstanding_orders(notify=self.notify_customers)

            # Build notification message
            self.notification.add_message(f"待處理訂單更新完成")
            self.notification.add_message(f"更新訂單狀態 {update_count} 筆")

            # Send notification
            if self.send_line_notification:
                self.notification.send_and_clear()
                pass

            logger.success(f"待處理訂單更新完成，共更新 {update_count} 筆")
            return True

        except Exception as e:
            logger.error(f"待處理訂單更新失敗: {e}")
            self.notification.add_message(f"待處理訂單更新失敗: {e}")

            if self.send_line_notification:
                self.notification.send_and_clear()

            return False
