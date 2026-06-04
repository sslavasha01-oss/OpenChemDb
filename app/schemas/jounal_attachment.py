from pydantic import BaseModel
from datetime import datetime
from typing import Optional

from app.models.journal_attachment import AttachmentType


class JournalAttachmentResponseSchema(BaseModel):
    id: int
    user_id: int
    journal_record_id: int
    type: AttachmentType
    description: Optional[str] = None
    file_path: str
    thumbnail_b64: Optional[str] = None
    date_added: datetime

    class Config:
        from_attributes = True