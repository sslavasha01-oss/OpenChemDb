import enum
from sqlalchemy import Column, Integer, String, Text, ForeignKey, Enum, DateTime, func, BigInteger

from app.core.db import Base


class AttachmentType(str, enum.Enum):
    ARTICLE = "ARTICLE"
    SPECTRUM = "SPECTRUM"
    MEDIA = "MEDIA"

class JournalAttachment(Base):
    __tablename__ = "journal_attachment"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    journal_record_id = Column(Integer, ForeignKey("user_journal.id", ondelete="CASCADE"), nullable=False)
    journal_record_ext_id = Column(Integer)
    type = Column(Enum(AttachmentType), nullable=False)
    description = Column(Text, nullable=True)
    file_path = Column(String(1000), nullable=False)
    thumbnail_b64 = Column(Text, nullable=True)
    date_added = Column(DateTime, server_default=func.now(), nullable=False)
    file_size = Column(BigInteger, server_default="0", default=0, nullable=False)