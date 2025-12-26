"""
Gmail repository for email operations.
"""
import imaplib
import email
import re
from email.header import decode_header
from email.utils import parsedate_to_datetime
from typing import List, Optional
from datetime import datetime
from loguru import logger

from src.models.email_attachment import EmailData, EmailAttachment, EmailSender
from src.config.config import SettingsManager


class GmailRepository:
    """
    Repository for Gmail IMAP operations.
    """

    def __init__(self, email_address: Optional[str] = None, password: Optional[str] = None):
        """
        Initialize Gmail repository.

        Args:
            email_address: Gmail address (uses config if not provided)
            password: App password (uses config if not provided)
        """
        settings = SettingsManager()
        self.email = email_address or settings.bot_gmail
        self.password = password or settings.bot_app_password
        self.mail: Optional[imaplib.IMAP4_SSL] = None

    def connect(self) -> bool:
        """
        Connect to Gmail IMAP server.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.mail = imaplib.IMAP4_SSL("imap.gmail.com")
            self.mail.login(self.email, self.password)
            self.mail.select("inbox")
            logger.success("Gmail IMAP 登錄成功")
            return True
        except Exception as e:
            logger.error(f"Gmail IMAP 登錄失敗: {e}")
            return False

    def disconnect(self) -> None:
        """Close the IMAP connection."""
        if self.mail:
            try:
                self.mail.close()
                self.mail.logout()
            except Exception as e:
                logger.warning(f"關閉 IMAP 連接時發生錯誤: {e}")

    def fetch_emails_by_date(
        self,
        target_sender: str,
        since_date: datetime,
        attachment_filter: Optional[str] = None
    ) -> List[EmailData]:
        """
        Fetch emails from a specific sender since a given date.

        Args:
            target_sender: Email address of the sender to filter
            since_date: Only fetch emails since this date
            attachment_filter: Optional string to filter attachment filenames

        Returns:
            List of EmailData objects
        """
        if not self.mail:
            if not self.connect():
                return []

        try:
            # Format date for IMAP search
            date_str = since_date.strftime("%d-%b-%Y")

            # Build search criteria
            # For ASCII-only filters, use X-GM-RAW for server-side filtering
            # For non-ASCII (Chinese), use basic search + client-side filtering
            is_ascii_filter = attachment_filter and attachment_filter.isascii() if attachment_filter else True

            if attachment_filter and is_ascii_filter:
                # Gmail search for ASCII filenames (faster, server-side)
                gmail_query_parts = [
                    "has:attachment",
                    f"filename:{attachment_filter}",
                    f"after:{since_date.strftime('%Y/%m/%d')}"
                ]
                if target_sender:
                    gmail_query_parts.append(f"from:{target_sender}")

                gmail_query = " ".join(gmail_query_parts)
                search_criteria = f'X-GM-RAW "{gmail_query}"'
                logger.info(f"IMAP 搜尋條件: {search_criteria}")
                status, messages = self.mail.search(None, search_criteria)
            else:
                # For Chinese filenames, search by date + sender, filter attachments client-side
                search_parts = [f'SINCE "{date_str}"']
                if target_sender:
                    search_parts.append(f'FROM "{target_sender}"')

                search_criteria = f'({" ".join(search_parts)})'
                logger.info(f"IMAP 搜尋條件: {search_criteria} (附件過濾: {attachment_filter})")
                status, messages = self.mail.search(None, search_criteria)
            if status != "OK":
                logger.warning(f"無法搜索郵件，搜索條件: {search_criteria}")
                return []

            message_ids = messages[0].split()
            if not message_ids:
                logger.info(f"沒有找到符合條件的郵件 (since {date_str})")
                return []

            logger.info(f"找到 {len(message_ids)} 封郵件，開始過濾...")

            # Note: Pre-filtering by BODYSTRUCTURE doesn't work well for Chinese filenames
            # because they are Base64 encoded. Just download and filter.

            results = []
            processed = 0
            for msg_id in message_ids:
                email_data = self._parse_email(msg_id, target_sender, attachment_filter)
                if email_data and email_data.has_attachments():
                    results.append(email_data)

            return results

        except Exception as e:
            logger.error(f"獲取郵件時發生錯誤: {e}")
            return []

    def _prefilter_by_attachment(
        self,
        message_ids: list,
        attachment_filter: str
    ) -> list:
        """
        Pre-filter emails by checking attachment names without downloading full content.
        Uses BODYSTRUCTURE which is much faster than RFC822.

        Args:
            message_ids: List of IMAP message IDs
            attachment_filter: String that attachment filename must contain

        Returns:
            Filtered list of message IDs
        """
        filtered = []

        for msg_id in message_ids:
            try:
                # Fetch only BODYSTRUCTURE (envelope + structure, not content)
                status, data = self.mail.fetch(msg_id, "(BODYSTRUCTURE)")
                if status != "OK":
                    continue

                # Parse BODYSTRUCTURE response to find attachment names
                bodystructure = str(data[0])

                # Look for attachment filename in the structure
                # BODYSTRUCTURE contains encoded filenames
                if attachment_filter in bodystructure:
                    filtered.append(msg_id)
                    continue

                # Also check for encoded Chinese characters (RFC 2047)
                # The filter might appear as =?UTF-8?B?...?= encoded
                import base64
                try:
                    encoded_filter = base64.b64encode(
                        attachment_filter.encode('utf-8')
                    ).decode('ascii')
                    if encoded_filter[:10] in bodystructure:  # Check partial match
                        filtered.append(msg_id)
                except Exception:
                    pass

            except Exception as e:
                # If we can't check, include it for full parsing
                logger.debug(f"預過濾檢查失敗: {e}")
                filtered.append(msg_id)

        return filtered

    def _parse_email(
        self,
        message_id: bytes,
        target_sender: str,
        attachment_filter: Optional[str] = None
    ) -> Optional[EmailData]:
        """
        Parse a single email message.

        Args:
            message_id: IMAP message ID
            target_sender: Expected sender email address
            attachment_filter: Optional string to filter attachment filenames

        Returns:
            EmailData if email matches criteria, None otherwise
        """
        try:
            status, data = self.mail.fetch(message_id, "(RFC822)")
            if status != "OK":
                return None

            raw_email = data[0][1]
            email_message = email.message_from_bytes(raw_email)

            # Parse sender
            sender_raw = self._decode_header_value(email_message["From"])
            sender_email = self._extract_email(sender_raw)

            # Check if sender matches (skip check if target_sender is empty)
            if target_sender and sender_email != target_sender:
                return None

            # Parse subject and date
            subject = self._decode_header_value(email_message["Subject"])
            date_str = email_message["Date"]
            try:
                parsed_date = parsedate_to_datetime(date_str)
            except Exception:
                parsed_date = datetime.now()

            # Parse attachments
            attachments = self._extract_attachments(email_message, attachment_filter)

            if not attachments:
                return None

            return EmailData(
                id=message_id.decode("utf-8"),
                subject=subject,
                sender=EmailSender(name=sender_raw, email=sender_email),
                date=parsed_date,
                attachments=attachments
            )

        except Exception as e:
            logger.error(f"解析郵件時發生錯誤: {e}")
            return None

    def _extract_attachments(
        self,
        email_message,
        filename_filter: Optional[str] = None
    ) -> List[EmailAttachment]:
        """
        Extract attachments from an email message.

        Args:
            email_message: Parsed email message
            filename_filter: Optional string that filename must contain

        Returns:
            List of EmailAttachment objects
        """
        attachments = []

        if not email_message.is_multipart():
            return attachments

        for part in email_message.walk():
            content_disposition = str(part.get("Content-Disposition"))
            if "attachment" not in content_disposition:
                continue

            filename = part.get_filename()
            if not filename:
                continue

            filename = self._decode_header_value(filename)

            # Apply filter if provided
            if filename_filter and filename_filter not in filename:
                continue

            content = part.get_payload(decode=True)
            if content:
                attachments.append(EmailAttachment(
                    filename=filename,
                    content=content,
                    content_type=part.get_content_type(),
                    size=len(content)
                ))

        return attachments

    def _decode_header_value(self, header_value: str) -> str:
        """Decode email header value handling various encodings."""
        if not header_value:
            return ""

        decoded_parts = []
        parts = decode_header(header_value)

        for part, encoding in parts:
            if isinstance(part, bytes):
                try:
                    decoded_parts.append(part.decode(encoding or "utf-8"))
                except Exception:
                    decoded_parts.append(part.decode("utf-8", errors="replace"))
            else:
                decoded_parts.append(str(part))

        return "".join(decoded_parts)

    def _extract_email(self, sender: str) -> str:
        """Extract email address from sender string."""
        email_match = re.search(r"<([^>]+)>", sender)
        if email_match:
            return email_match.group(1)

        email_match = re.search(r"[\w\.-]+@[\w\.-]+", sender)
        if email_match:
            return email_match.group(0)

        return ""

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
        return False
