import datetime
import enum

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship

from app.core.db import Base


# Предполагается, что Base импортируется из вашего модуля инициализации БД
# from app.database import Base

class ProcessStatus(str, enum.Enum):
    PROCESSING_EXPORT = "PROCESSING_EXPORT"
    PROCESSING_IMPORT = "PROCESSING_IMPORT"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class Type(str, enum.Enum):
    EXPORT = "EXPORT"
    IMPORT = "IMPORT"

class UserExport(Base):
    __tablename__ = "exports"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type = Column(Enum(Type, name="processtype"), nullable=False, index=True)
    status = Column(Enum(ProcessStatus), nullable=True)  # Статус текущего процесса
    error_message = Column(String, nullable=True)  # Если упало, сохраним причину
    path = Column(String, nullable=True)  # Будет содержать относительный путь: "tmp/journal_export.zip"
    created_date = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)