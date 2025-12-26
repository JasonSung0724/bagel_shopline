"""
Daily workflow orchestrator.
Coordinates the daily order processing workflow.
"""

from datetime import datetime, timedelta
from typing import Optional
from loguru import logger

from src.services.email_service import EmailService
from src.services.c2c_service import C2CService
from src.services.shopline_service import ShopLineService
from src.services.notification_service import NotificationService


class DailyWorkflow:
    """
    Orchestrates the daily order processing workflow.

    Flow:
    1. Fetch emails from Flowtide
    2. Process C2C orders -> Update Google Sheet
    3. Process ShopLine orders -> Update via API
    4. Send LINE notification
    """

    def __init__(self, notify_customers: bool = False):
        """
        Initialize daily workflow.

        Args:
            notify_customers: Whether to send customer notifications for ShopLine updates
        """
        self.email_service = EmailService()
        self.c2c_service = C2CService()
        self.shopline_service = ShopLineService()
        self.notification = NotificationService()
        self.notify_customers = notify_customers

    def run(self, target_date: Optional[datetime] = None) -> bool:
        """
        Run the complete daily workflow.

        Args:
            target_date: Date to process (default: yesterday)

        Returns:
            True if workflow completed successfully
        """
        try:
            # Default to yesterday
            if target_date is None:
                target_date = datetime.now() - timedelta(days=1)

            date_str = target_date.strftime("%Y-%m-%d")
            logger.info(f"開始執行每日更新 - 目標日期: {date_str}")

            # Step 1: Fetch emails
            success = self._step_fetch_emails(target_date)
            if not success:
                self._send_notification()
                return False

            # Step 2: Process C2C orders
            self._step_process_c2c()

            # Step 3: Process ShopLine orders
            self._step_process_shopline()

            # Step 4: Send notification
            self._send_notification()

            logger.success("每日更新訂單資訊完成")
            return True

        except Exception as e:
            logger.error(f"每日更新訂單資訊失敗: {e}")
            self.notification.add_message(f"每日更新訂單資訊失敗: {e}")
            self._send_notification()
            return False

    def _step_fetch_emails(self, target_date: datetime) -> bool:
        """Step 1: Fetch Flowtide emails."""
        logger.info("Step 1: 獲取逢泰郵件")

        self._emails = self.email_service.fetch_flowtide_emails(target_date)
        date_str = target_date.strftime("%d-%b-%Y")

        if self._emails:
            self.notification.add_message(f"今天有收到逢泰Excel ({date_str})")
            return True
        else:
            self.notification.add_message(f"今天沒有收到逢泰Excel ({date_str})")
            return False

    def _step_process_c2c(self) -> None:
        """Step 2: Process C2C orders and update Google Sheet."""
        logger.info("Step 2: 處理 C2C 訂單")

        # Extract C2C orders from email
        c2c_orders, total_count = self.email_service.extract_orders_from_emails(self._emails, platform="c2c")

        if not c2c_orders:
            self.notification.add_message("逢泰Excel中沒有 C2C 訂單")
            return

        self.notification.add_message(f"C2C訂單-總計 {total_count} 筆, 黑貓託運單號共 {len(c2c_orders)} 筆")

        # Build order status dict
        order_status_dict = self.c2c_service.build_order_status_dict(c2c_orders)

        # Process each target sheet
        target_sheets = self.c2c_service.get_target_sheets()

        for sheet_name in target_sheets:
            self.notification.add_message(f"Google Sheet: {sheet_name}")

            update_count, error = self.c2c_service.process_sheet(sheet_name, order_status_dict)

            if error:
                self.notification.add_message(f"處理失敗: {error}")
            elif update_count > 0:
                self.notification.add_message(f"成功更新了 {update_count} 筆資料")
            else:
                self.notification.add_message("執行完畢 沒有更新任何資料")

    def _step_process_shopline(self) -> None:
        """Step 3: Process ShopLine orders."""
        logger.info("Step 3: 處理 ShopLine 訂單")

        # Extract ShopLine orders from email
        shopline_orders, total_count = self.email_service.extract_orders_from_emails(self._emails, platform="shopline")

        if not shopline_orders:
            self.notification.add_message("逢泰Excel中沒有 SHOPLINE 訂單")
            return

        self.notification.add_message(f"SHOPLINE訂單-總計 {total_count} 筆, 黑貓託運單號共 {len(shopline_orders)} 筆")

        # Process orders
        tracking_count, status_count = self.shopline_service.process_email_orders(shopline_orders, notify=self.notify_customers)

        self.notification.add_message(f"ShopLine訂單-更新追蹤資訊 {tracking_count} 筆, 更新訂單狀態 {status_count} 筆")

    def _send_notification(self) -> None:
        """Send LINE notification."""
        logger.info("Step 4: 發送 LINE 通知")
        self.notification.send_and_clear()
