import imaplib
import email
from email.header import decode_header
import os
import datetime
import re
import base64
from email.utils import parsedate_to_datetime


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
            print("登錄成功！")
        except Exception as e:
            print(f"登錄失敗: {e}")
            return

    def search_emails(self, date):
        search_criteria = f'(SINCE "{date}")'
        status, messages = self.mail.search(None, search_criteria)
        if status != "OK":
            print(f"無法搜索郵件，搜索條件: {search_criteria}")
            return
        message_ids = messages[0].split()
        total_messages = len(message_ids)
        if total_messages == 0:
            print("今天沒有郵件")
            self.connect_close()
            return
        print(f"找到 {total_messages} 封郵件")
        return message_ids

    def connect_close(self):
        self.mail.close()
        self.mail.logout()

    def download_attach(self, file, filename):
        filepath = os.path.join("order_excel", filename)
        with open(filepath, "wb") as f:
            f.write(file)

    def parse_email(self, message_id):
        status, data = self.mail.fetch(message_id, "(RFC822)")
        if status != "OK":
            print(f"無法獲取郵件內容，郵件ID: {message_id}")
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
                            self.download_attach(file=attachment_data, filename=filename)
                            attachments.append(
                                {
                                    "filename": filename,
                                    "content_type": content_type,
                                    "size": len(attachment_data),
                                }
                            )
        if sender_email == "jason870724@gmail.com":
            for attach in attachments:
                if attach and "A442" in attach["filename"]:
                    email_data = {
                        "id": message_id.decode("utf-8"),
                        "subject": subject,
                        "sender": {"name": sender, "email": sender_email},
                        "date": formatted_date,
                        "attachments": attachments,
                    }
                    return email_data
        return None

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


if __name__ == "__main__":
    today = datetime.datetime.now().strftime("%d-%b-%Y")
    script = GmailConnect(email="bagelshop2025@gmail.com", password="ciyc avqe zlsu bfcg")
    messages = script.search_emails(today)
    for message in messages:
        data = script.parse_email(message)
    if data:
        print(data)
