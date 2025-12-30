"""
Email service for fetching and processing emails.
"""

import io
import pandas as pd
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from loguru import logger

from src.repositories.gmail_repository import GmailRepository
from src.models.email_attachment import EmailData
from src.config.config import ConfigManager


class EmailService:
    """
    Service for email operations and Excel processing.
    """

    def __init__(self):
        """Initialize email service."""
        self.gmail_repo = GmailRepository()
        self.config = ConfigManager()

    def fetch_flowtide_emails(self, target_date: datetime) -> List[EmailData]:
        """
        Fetch Flowtide Excel emails for a specific date.

        Args:
            target_date: Date to fetch emails for

        Returns:
            List of EmailData objects with Flowtide attachments
        """
        with self.gmail_repo as repo:
            emails = repo.fetch_emails_by_date(
                target_sender=self.config.flowtide_sender_email, since_date=target_date, attachment_filter="A442", strict_attachment_filter="A442_QC_"
            )

        date_str = target_date.strftime("%d-%b-%Y")
        if emails:
            logger.success(f"收到逢泰 Excel ({date_str}), 共 {len(emails)} 封郵件")
        else:
            logger.warning(f"沒有收到逢泰 Excel ({date_str})")

        return emails

    def extract_orders_from_emails(self, emails: List[EmailData], platform: str = "c2c") -> Tuple[List[Dict], int]:
        """
        Extract order information from email attachments.

        Args:
            emails: List of EmailData objects
            platform: Platform to filter ("c2c" or "shopline")

        Returns:
            Tuple of (list of order dicts, total order count)
        """
        orders = []
        total_count = 0
        processed_tcat_numbers = set()

        for email_data in emails:
            for attachment in email_data.attachments:
                try:
                    excel_orders, count = self._process_excel_attachment(attachment.content, platform, processed_tcat_numbers)
                    orders.extend(excel_orders)
                    total_count += count
                except Exception as e:
                    logger.error(f"處理附件 {attachment.filename} 失敗: {e}")

        logger.info(f"{platform.upper()} 訂單: 總計 {total_count} 筆, 黑貓單號 {len(processed_tcat_numbers)} 筆")
        return orders, total_count

    def _process_excel_attachment(self, content: bytes, platform: str, processed_tcat_numbers: set) -> Tuple[List[Dict], int]:
        """
        Process a single Excel attachment.

        Args:
            content: Excel file content
            platform: Platform to filter
            processed_tcat_numbers: Set of already processed tracking numbers

        Returns:
            Tuple of (list of order dicts, order count)
        """
        file = io.BytesIO(content)
        df = pd.read_excel(file, dtype={self.config.flowtide_order_number: str})

        orders = []
        count = 0

        for _, row in df.iterrows():
            if not self._is_platform_order(row, platform):
                continue

            count += 1
            order_number = self._get_order_number(row, platform)
            tcat_number = row.get(self.config.flowtide_tcat_number)

            if pd.notna(tcat_number):
                tcat_number = str(int(tcat_number))
                if tcat_number not in processed_tcat_numbers:
                    processed_tcat_numbers.add(tcat_number)
                    orders.append({"order_number": order_number, "tcat_number": tcat_number, "platform": platform})

        return orders, count

    def _is_platform_order(self, row: pd.Series, platform: str) -> bool:
        """
        Check if a row belongs to the specified platform.

        Args:
            row: DataFrame row
            platform: Platform to check ("c2c" or "shopline")

        Returns:
            True if row belongs to platform
        """
        try:
            if platform == "c2c":
                mark = row.get(self.config.flowtide_mark_field, "")
                return str(mark).startswith(self.config.flowtide_c2c_mark)
            elif platform == "shopline":
                order_num = str(row.get(self.config.flowtide_order_number, ""))
                delivery_company = row.get(self.config.flowtide_delivery_company, "")
                return order_num.startswith("#") and delivery_company == "TCAT"
            return False
        except Exception as e:
            logger.debug(f"檢查平台訂單失敗: {e}")
            return False

    def _get_order_number(self, row: pd.Series, platform: str) -> str:
        """
        Extract order number from row.

        Args:
            row: DataFrame row
            platform: Platform type

        Returns:
            Order number string
        """
        raw_number = str(row.get(self.config.flowtide_order_number, ""))

        if platform == "c2c":
            return raw_number
        elif platform == "shopline":
            # Remove # prefix
            return raw_number.lstrip("#").split("-")[0]

        return raw_number
