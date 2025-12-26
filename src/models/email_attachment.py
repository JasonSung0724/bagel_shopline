"""
Email-related data models.
"""
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime


@dataclass
class EmailAttachment:
    """
    Represents an email attachment.
    """
    filename: str
    content: bytes
    content_type: str
    size: int


@dataclass
class EmailSender:
    """
    Represents an email sender.
    """
    name: str
    email: str


@dataclass
class EmailData:
    """
    Represents parsed email data.
    """
    id: str
    subject: str
    sender: EmailSender
    date: datetime
    attachments: List[EmailAttachment] = field(default_factory=list)

    def has_attachments(self) -> bool:
        """Check if email has attachments."""
        return len(self.attachments) > 0

    def get_excel_attachments(self) -> List[EmailAttachment]:
        """Get only Excel file attachments."""
        excel_types = [
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.ms-excel",
        ]
        return [
            att for att in self.attachments
            if att.content_type in excel_types or att.filename.endswith(('.xlsx', '.xls'))
        ]

    def get_flowtide_attachments(self) -> List[EmailAttachment]:
        """Get Flowtide Excel attachments (filename contains 'A442_QC_')."""
        return [
            att for att in self.attachments
            if "A442_QC_" in att.filename
        ]
