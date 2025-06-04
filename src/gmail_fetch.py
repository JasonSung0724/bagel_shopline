import imaplib
import email
from email.header import decode_header
import datetime
import re
from email.utils import parsedate_to_datetime
from loguru import logger
from src.config.config import ConfigManager


CONFIG = ConfigManager()


class GmailConnect:

    def __init__(self, email, password):
        self.email = email
        self.password = password
        self.mail = imaplib.IMAP4_SSL("imap.gmail.com")
        self.mail_login()
        self.mail.select("inbox")

    def mail_login(self):
        try:
            self.mail.login(self.email, self.password)
            logger.success("登錄成功！")
        except Exception as e:
            logger.error(f"登錄失敗: {e}")
            return

    def search_emails(self, date):
        search_criteria = f'(SINCE "{date}")'
        status, messages = self.mail.search(None, search_criteria)
        if status != "OK":
            logger.warning(f"無法搜索郵件，搜索條件: {search_criteria}")
            return
        message_ids = messages[0].split()
        total_messages = len(message_ids)
        if total_messages == 0:
            logger.warning("今天沒有郵件")
            self.connect_close()
            return
        logger.info(f"找到 {total_messages} 封郵件")
        return message_ids

    def connect_close(self):
        self.mail.close()
        self.mail.logout()

    def get_attachments(self, target_sender_email):
        messages = self._fetch_email()
        result = []
        if messages:
            for message in messages:
                data = self.parse_email(message, target_sender_email)
                if data and "attachments" in data and data["attachments"]:
                    logger.info(data["attachments"][0]["filename"])
                    result.append(data)
        return result

    def _fetch_email(self):
        today = datetime.datetime.now()
        previous_day = today - datetime.timedelta(days=1)
        date_format = "%d-%b-%Y"
        previous_day_str = previous_day.strftime(date_format)
        today_str = today.strftime(date_format)
        messages = self.search_emails(previous_day_str)
        return messages

    def get_shopline_verification_code(self, target_sender_email):
        messages = self._fetch_email()
        result = []
        if messages:
            for message in messages:
                data = self.parse_email_shopline_verification_code(message, target_sender_email)
                if data and "subject" in data and ("code" in data["subject"] or "驗證碼" in data["subject"]):
                    result.append(data)
        if result:
            mail = max(result, key=lambda x: x["date"])
            code = re.search(r"\d{6}", mail["subject"])
            if code:
                return code.group(0)
        return None

    def parse_email(self, message_id, target_sender_email):
        status, data = self.mail.fetch(message_id, "(RFC822)")
        if status != "OK":
            logger.warning(f"無法獲取郵件內容，郵件ID: {message_id}")
            return None

        raw_email = data[0][1]
        email_message = email.message_from_bytes(raw_email)
        subject = self._decode_header_value(email_message["Subject"])
        sender = self._decode_header_value(email_message["From"])
        date_str = email_message["Date"]
        try:
            date = parsedate_to_datetime(date_str)
            formatted_date = date.strftime("%Y-%m-%d %H:%M:%S")
        except:
            formatted_date = date_str
        sender_email = ""
        email_match = re.search(r"<([^>]+)>", sender)
        if email_match:
            sender_email = email_match.group(1)
        else:
            email_match = re.search(r"[\w\.-]+@[\w\.-]+", sender)
            if email_match:
                sender_email = email_match.group(0)
        attachments = []

        if email_message.is_multipart():
            for part in email_message.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))
                if "attachment" in content_disposition:
                    filename = part.get_filename()
                    if filename:
                        filename = self._decode_header_value(filename)
                        attachment_data = part.get_payload(decode=True)
                        if attachment_data:
                            attachments.append(
                                {
                                    "file": attachment_data,
                                    "filename": filename,
                                    "content_type": content_type,
                                    "size": len(attachment_data),
                                }
                            )
        if sender_email == target_sender_email:
            for attach in attachments:
                if attach and "A442_QC_" in attach["filename"]:
                    email_data = {
                        "id": message_id.decode("utf-8"),
                        "subject": subject,
                        "sender": {"name": sender, "email": sender_email},
                        "date": formatted_date,
                        "attachments": attachments,
                    }
                    return email_data
        return None

    def parse_email_shopline_verification_code(self, message_id, target_sender_email):
        status, data = self.mail.fetch(message_id, "(RFC822)")
        raw_email = data[0][1]
        email_message = email.message_from_bytes(raw_email)
        subject = self._decode_header_value(email_message["Subject"])
        sender = self._decode_header_value(email_message["From"])
        sender_email = ""
        email_match = re.search(r"<([^>]+)>", sender)
        if email_match:
            sender_email = email_match.group(1)
        else:
            email_match = re.search(r"[\w\.-]+@[\w\.-]+", sender)
            if email_match:
                sender_email = email_match.group(0)
        date_str = email_message["Date"]
        send_date = parsedate_to_datetime(date_str)

        attachments = []
        email_data = {}
        if sender_email == target_sender_email:
            email_data = {
                "id": message_id.decode("utf-8"),
                "subject": subject,
                "sender": {"name": sender, "email": sender_email},
                "date": send_date,
                "attachments": attachments,
            }
        return email_data

    def _decode_header_value(self, header_value):
        if not header_value:
            return ""
        decoded_parts = []
        parts = decode_header(header_value)
        for part, encoding in parts:
            if isinstance(part, bytes):
                try:
                    decoded_parts.append(part.decode(encoding or "utf-8"))
                except:
                    decoded_parts.append(part.decode("utf-8", errors="replace"))
            else:
                decoded_parts.append(str(part))
        return "".join(decoded_parts)
