"""
C2C order service for Google Sheet operations.
"""
import pandas as pd
from typing import Dict, List, Optional, Tuple
from loguru import logger

from src.repositories.gsheet_repository import GoogleSheetRepository
from src.repositories.tcat_repository import TcatRepository
from src.config.config import ConfigManager


class C2CService:
    """
    Service for C2C order management in Google Sheets.
    """

    def __init__(self):
        """Initialize C2C service."""
        self.gsheet_repo = GoogleSheetRepository()
        self.tcat_repo = TcatRepository()
        self.config = ConfigManager()

        # Field names from config
        self.order_number_field = self.config.c2c_order_number
        self.delivery_number_field = self.config.c2c_delivery_number
        self.status_field = self.config.c2c_current_status
        self.shipping_date_field = self.config.c2c_shipping_date

        # Status values
        self.success_status = self.config.c2c_status_success
        self.no_data_status = self.config.c2c_status_no_data
        self.collected_status = self.config.c2c_status_collected

    def get_target_sheets(self) -> List[str]:
        """
        Get all C2C tracking sheets.

        Returns:
            List of sheet names
        """
        return self.gsheet_repo.find_c2c_sheets()

    def process_sheet(
        self,
        sheet_name: str,
        email_orders: Dict[str, Dict]
    ) -> Tuple[int, Optional[str]]:
        """
        Process a single C2C sheet with order updates.

        Args:
            sheet_name: Name of the sheet to process
            email_orders: Dict of {order_number: {status, tcat_number}} from email

        Returns:
            Tuple of (update_count, error_message or None)
        """
        try:
            # Open sheet and get data
            if not self.gsheet_repo.open_sheet(sheet_name):
                return 0, f"無法開啟工作表 {sheet_name}"

            worksheet = self.gsheet_repo.get_worksheet(0)
            all_values = self.gsheet_repo.get_all_values(worksheet)

            if not all_values:
                return 0, "工作表為空"

            # Backup first
            backup_name = self.config.flowdite_backup_sheet
            if not self._backup_sheet(all_values, backup_name):
                return 0, "備份失敗"

            # Reopen original sheet
            self.gsheet_repo.open_sheet(sheet_name)
            worksheet = self.gsheet_repo.get_worksheet(0)

            # Convert to DataFrame
            df = self._values_to_dataframe(all_values)

            # Process each row
            update_count = 0
            for index, row in df.iterrows():
                order_number = row.get(self.order_number_field)
                if pd.isna(order_number) or not str(order_number).strip():
                    continue

                updated = self._process_row(df, index, row, email_orders)
                if updated:
                    update_count += 1

            # Update sheet if changes were made
            if update_count > 0:
                if self.gsheet_repo.update_worksheet(worksheet, df):
                    # Verify backup
                    is_equal, msg = self.gsheet_repo.compare_row_counts(
                        sheet_name, backup_name
                    )
                    if not is_equal:
                        logger.warning(f"行數驗證警告: {msg}")

                    logger.success(f"成功更新 {update_count} 筆資料")
                else:
                    return update_count, "更新工作表失敗"

            return update_count, None

        except Exception as e:
            logger.error(f"處理工作表 {sheet_name} 失敗: {e}")
            return 0, str(e)

    def _backup_sheet(self, data: List[List], backup_name: str) -> bool:
        """Backup sheet data."""
        return self.gsheet_repo.backup_to_sheet(data, backup_name)

    def _values_to_dataframe(self, values: List[List]) -> pd.DataFrame:
        """Convert sheet values to DataFrame."""
        header = [col for col in values[0] if col != ""]
        header_count = len(header)
        data = [row[:header_count] for row in values[1:]]
        df = pd.DataFrame(data, columns=header)
        return df.reset_index(drop=True)

    def _process_row(
        self,
        df: pd.DataFrame,
        index: int,
        row: pd.Series,
        email_orders: Dict[str, Dict]
    ) -> bool:
        """
        Process a single row for updates.

        Args:
            df: DataFrame to update
            index: Row index
            row: Row data
            email_orders: Email order data

        Returns:
            True if row was updated
        """
        order_number = str(row.get(self.order_number_field, "")).strip()
        tcat_number = row.get(self.delivery_number_field)
        current_status = row.get(self.status_field)

        # Skip if already delivered
        if tcat_number and current_status == self.success_status:
            return False

        # Has tracking number - just update status
        if pd.notna(tcat_number) and str(tcat_number).strip():
            tcat_number = str(tcat_number).strip()
            return self._update_status(df, index, row, tcat_number)

        # No tracking number - try to get from email
        if order_number in email_orders:
            order_info = email_orders[order_number]
            tcat_number = order_info.get("tcat_number")
            status = order_info.get("status")

            if tcat_number:
                df.loc[index, self.delivery_number_field] = tcat_number
                logger.debug(f"更新 {order_number} 的黑貓單號: {tcat_number}")
                return self._update_status_value(df, index, row, status)

        return False

    def _update_status(
        self,
        df: pd.DataFrame,
        index: int,
        row: pd.Series,
        tcat_number: str
    ) -> bool:
        """
        Update status by querying Tcat.

        Args:
            df: DataFrame to update
            index: Row index
            row: Row data
            tcat_number: Tracking number

        Returns:
            True if updated
        """
        new_status = self.tcat_repo.get_order_status(tcat_number)
        return self._update_status_value(df, index, row, new_status)

    def _update_status_value(
        self,
        df: pd.DataFrame,
        index: int,
        row: pd.Series,
        new_status: str
    ) -> bool:
        """
        Apply status update to DataFrame.

        Args:
            df: DataFrame to update
            index: Row index
            row: Row data
            new_status: New status value

        Returns:
            True if updated
        """
        if new_status == self.no_data_status:
            return False

        current_status = row.get(self.status_field)
        shipping_date = row.get(self.shipping_date_field)
        tcat_number = row.get(self.delivery_number_field)
        updated = False

        # Update status if different
        if current_status != new_status:
            df.loc[index, self.status_field] = new_status
            logger.debug(f"更新狀態: {current_status} -> {new_status}")
            updated = True

        # Update shipping date if empty
        if pd.isna(shipping_date) or not str(shipping_date).strip():
            if pd.notna(tcat_number):
                collected_time = self.tcat_repo.get_collected_time(
                    str(tcat_number).strip(),
                    current_status=new_status
                )
                if collected_time:
                    df.loc[index, self.shipping_date_field] = collected_time
                    logger.debug(f"更新集貨時間: {collected_time}")
                    updated = True

        return updated

    def build_order_status_dict(
        self,
        orders: List[Dict]
    ) -> Dict[str, Dict]:
        """
        Build order status dictionary by querying Tcat.

        Args:
            orders: List of order dicts from email

        Returns:
            Dict of {order_number: {status, tcat_number}}
        """
        result = {}

        for order in orders:
            order_number = order.get("order_number")
            tcat_number = order.get("tcat_number")

            if order_number and tcat_number:
                status = self.tcat_repo.get_order_status(tcat_number)
                result[order_number] = {
                    "status": status,
                    "tcat_number": tcat_number
                }

        logger.info(f"建立 {len(result)} 筆訂單狀態")
        return result
