"""
Notification service for LINE messages.
"""
from typing import Optional, List
from loguru import logger
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi
from linebot.v3.messaging import TextMessage, PushMessageRequest

from src.config.config import SettingsManager


class NotificationService:
    """
    Service for sending notifications via LINE.
    """

    def __init__(self):
        """Initialize notification service."""
        settings = SettingsManager()
        self.line_access_token = settings.line_access_token
        self.group_id = settings.group_id
        self._messages: List[str] = []

    def add_message(self, message: str) -> None:
        """
        Add a message to the queue.

        Args:
            message: Message to add
        """
        self._messages.append(str(message))

    def clear_messages(self) -> None:
        """Clear all queued messages."""
        self._messages = []

    def get_combined_message(self) -> Optional[str]:
        """
        Get all messages combined into one string.

        Returns:
            Combined message or None if empty
        """
        if not self._messages:
            return None
        return "\n".join(self._messages)

    def send_line_message(self, message: Optional[str] = None) -> bool:
        """
        Send message to LINE group.

        Args:
            message: Message to send (uses queued messages if not provided)

        Returns:
            True if successful, False otherwise
        """
        text = message or self.get_combined_message()
        if not text:
            logger.warning("沒有訊息可發送")
            return False

        configuration = Configuration(access_token=self.line_access_token)

        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            try:
                push_request = PushMessageRequest(
                    to=self.group_id,
                    messages=[TextMessage(text=text)]
                )
                response = line_bot_api.push_message(push_request)
                logger.success(f"LINE 訊息發送成功")
                self.clear_messages()
                return True
            except Exception as e:
                logger.error(f"LINE 訊息發送失敗: {e}")
                return False

    def send_and_clear(self) -> bool:
        """
        Send all queued messages and clear the queue.

        Returns:
            True if successful, False otherwise
        """
        result = self.send_line_message()
        self.clear_messages()
        return result

    @property
    def has_messages(self) -> bool:
        """Check if there are queued messages."""
        return len(self._messages) > 0

    @property
    def message_count(self) -> int:
        """Get the number of queued messages."""
        return len(self._messages)
