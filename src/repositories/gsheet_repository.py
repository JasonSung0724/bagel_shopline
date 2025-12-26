"""
Google Sheets repository for spreadsheet operations.
"""
import pandas as pd
from typing import List, Dict, Optional, Any
from loguru import logger

from src.google_drive import C2CGoogleSheet
from src.config.config import ConfigManager


class GoogleSheetRepository:
    """
    Repository for Google Sheets operations.
    """

    def __init__(self):
        """Initialize Google Sheet repository."""
        self.drive = C2CGoogleSheet()
        self.config = ConfigManager()
        self._current_sheet = None
        self._current_worksheet = None

    def get_all_sheets(self) -> Dict[str, str]:
        """
        Get all available Google Sheets.

        Returns:
            Dictionary of {sheet_name: sheet_id}
        """
        return self.drive.get_all_sheets() or {}

    def find_c2c_sheets(self) -> List[str]:
        """
        Find all C2C tracking sheets.

        Returns:
            List of sheet names matching C2C format
        """
        sheets = self.get_all_sheets()
        return self.drive.find_c2c_track_sheet(sheets)

    def open_sheet(self, sheet_name: str) -> bool:
        """
        Open a Google Sheet by name.

        Args:
            sheet_name: Name of the sheet to open

        Returns:
            True if successful, False otherwise
        """
        try:
            self.drive.open_sheet(sheet_name)
            self._current_sheet = sheet_name
            return True
        except Exception as e:
            logger.error(f"無法開啟工作表 {sheet_name}: {e}")
            return False

    def get_worksheet(self, index: int = 0):
        """
        Get a worksheet by index.

        Args:
            index: Worksheet index (default 0)

        Returns:
            Worksheet object
        """
        self._current_worksheet = self.drive.get_worksheet(index)
        return self._current_worksheet

    def get_all_values(self, worksheet=None) -> List[List[Any]]:
        """
        Get all values from a worksheet.

        Args:
            worksheet: Worksheet object (uses current if not provided)

        Returns:
            2D list of cell values
        """
        ws = worksheet or self._current_worksheet
        if ws:
            return self.drive.get_worksheet_all_values(ws)
        return []

    def get_as_dataframe(self, worksheet=None) -> pd.DataFrame:
        """
        Get worksheet data as a Pandas DataFrame.

        Args:
            worksheet: Worksheet object (uses current if not provided)

        Returns:
            DataFrame with worksheet data
        """
        values = self.get_all_values(worksheet)
        if not values:
            return pd.DataFrame()

        # Filter empty header columns
        header = [col for col in values[0] if col != ""]
        header_count = len(header)

        # Trim data to header columns
        data = [row[:header_count] for row in values[1:]]

        df = pd.DataFrame(data, columns=header)
        return df.reset_index(drop=True)

    def update_worksheet(
        self,
        worksheet,
        df: pd.DataFrame,
        protected_columns: int = 12
    ) -> bool:
        """
        Update worksheet with DataFrame data.
        Only updates columns after protected_columns.

        Args:
            worksheet: Worksheet to update
            df: DataFrame with data
            protected_columns: Number of columns to protect (default 12)

        Returns:
            True if successful, False otherwise
        """
        try:
            return self.drive.update_worksheet(worksheet, df)
        except Exception as e:
            logger.error(f"更新工作表失敗: {e}")
            return False

    def backup_to_sheet(
        self,
        source_data: List[List[Any]],
        backup_sheet_name: str
    ) -> bool:
        """
        Backup data to a backup sheet.

        Args:
            source_data: Data to backup
            backup_sheet_name: Name of backup sheet

        Returns:
            True if successful, False otherwise
        """
        try:
            self.open_sheet(backup_sheet_name)
            backup_worksheet = self.get_worksheet(0)

            if not source_data:
                return False

            required_rows = len(source_data)
            required_cols = len(source_data[0]) if source_data else 0

            # Expand worksheet if needed
            current_rows = backup_worksheet.rows
            current_cols = backup_worksheet.cols

            if required_rows > current_rows or required_cols > current_cols:
                logger.info(f"擴展備份工作表: {current_rows}x{current_cols} -> {required_rows}x{required_cols}")
                backup_worksheet.resize(rows=required_rows, cols=required_cols)

            # Update values
            end_col = chr(64 + required_cols) if required_cols <= 26 else 'Z'
            backup_worksheet.update_values(
                crange=f"A1:{end_col}{required_rows}",
                values=source_data
            )

            logger.success(f"成功備份到 {backup_sheet_name}")
            return True

        except Exception as e:
            logger.error(f"備份失敗: {e}")
            return False

    def compare_row_counts(
        self,
        sheet1_name: str,
        sheet2_name: str
    ) -> tuple[bool, str]:
        """
        Compare row counts between two sheets.

        Args:
            sheet1_name: First sheet name
            sheet2_name: Second sheet name

        Returns:
            Tuple of (is_equal, message)
        """
        try:
            # Get first sheet data
            self.open_sheet(sheet1_name)
            ws1 = self.get_worksheet(0)
            data1 = self.get_all_values(ws1)

            # Get second sheet data
            self.open_sheet(sheet2_name)
            ws2 = self.get_worksheet(0)
            data2 = self.get_all_values(ws2)

            # Filter empty rows
            def count_valid_rows(data):
                return len([
                    row for row in data
                    if any(cell.strip() if isinstance(cell, str) else cell for cell in row)
                ])

            count1 = count_valid_rows(data1)
            count2 = count_valid_rows(data2)

            if count1 == count2:
                msg = f"有效行數相同: {sheet1_name}={count1}行, {sheet2_name}={count2}行"
                return True, msg
            else:
                msg = f"有效行數不同: {sheet1_name}={count1}行, {sheet2_name}={count2}行"
                return False, msg

        except Exception as e:
            return False, f"比較失敗: {e}"
