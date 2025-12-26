"""
Tcat (黑貓宅急便) repository for delivery status queries.
Wraps the existing tcat_scraping module.
"""
from typing import Optional
from loguru import logger

from src.tcat_scraping import Tcat
from src.config.config import ConfigManager


class TcatRepository:
    """
    Repository for Tcat delivery status operations.
    Encapsulates the web scraping logic.
    """

    def __init__(self):
        """Initialize Tcat repository."""
        self.config = ConfigManager()
        self.no_data_status = self.config.c2c_status_no_data
        self.collected_status = self.config.c2c_status_collected

    def get_order_status(self, tracking_number: str) -> str:
        """
        Get the current delivery status for a tracking number.

        Args:
            tracking_number: Tcat tracking number

        Returns:
            Status string (e.g., "已集貨", "順利送達", "尚無資料")
        """
        try:
            status = Tcat.order_status(tracking_number)
            logger.debug(f"黑貓單號 {tracking_number} 狀態: {status}")
            return status
        except Exception as e:
            logger.error(f"查詢黑貓狀態失敗 {tracking_number}: {e}")
            return self.no_data_status

    def get_collected_time(
        self,
        tracking_number: str,
        current_status: Optional[str] = None
    ) -> Optional[str]:
        """
        Get the collection time for a tracking number.

        Args:
            tracking_number: Tcat tracking number
            current_status: Current status (for optimization)

        Returns:
            Collection time string (format: YYYYMMDD) or None
        """
        try:
            collected_time = Tcat.order_detail_find_collected_time(
                tracking_number,
                current_state=current_status
            )
            if collected_time:
                logger.debug(f"黑貓單號 {tracking_number} 集貨時間: {collected_time}")
            return collected_time
        except Exception as e:
            logger.error(f"查詢集貨時間失敗 {tracking_number}: {e}")
            return None

    def get_status_update_time(self, tracking_number: str) -> Optional[str]:
        """
        Get the last status update time.

        Args:
            tracking_number: Tcat tracking number

        Returns:
            Update time string (format: YYYYMMDD) or None
        """
        try:
            update_time = Tcat.current_state_update_time(tracking_number)
            return update_time if update_time else None
        except Exception as e:
            logger.error(f"查詢更新時間失敗 {tracking_number}: {e}")
            return None

    @staticmethod
    def get_tracking_url(tracking_number: str) -> str:
        """
        Get the tracking URL for a tracking number.

        Args:
            tracking_number: Tcat tracking number

        Returns:
            Tracking URL string
        """
        return Tcat.get_query_url(tracking_number)

    def is_delivered(self, status: str) -> bool:
        """Check if status indicates delivery is complete."""
        return status == self.config.c2c_status_success

    def is_collected(self, status: str) -> bool:
        """Check if status indicates package is collected."""
        return status == self.collected_status

    def has_data(self, status: str) -> bool:
        """Check if status has actual data."""
        return status != self.no_data_status
