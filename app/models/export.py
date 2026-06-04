import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship

from app.core.db import Base


# Предполагается, что Base импортируется из вашего модуля инициализации БД
# from app.database import Base

class UserExport(Base):
    __tablename__ = "exports"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    path = Column(String, nullable=True)  # Будет содержать относительный путь: "tmp/journal_export.zip"
    created_date = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)