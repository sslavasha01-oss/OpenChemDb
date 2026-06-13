from enum import Enum

from sqlalchemy import String, Boolean, Integer, BigInteger
from sqlalchemy.orm import Mapped, mapped_column
from app.core.db import Base

class TariffPlan(str, Enum):
    FREE = "FREE"
    PAID_1 = "PAID_1"

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, default="USER", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    attachments_total_size: Mapped[int] = mapped_column(BigInteger, server_default="0", default=0, nullable=False)
    tariff_plan: Mapped[str] = mapped_column(String(50), server_default="FREE", default="FREE", nullable=False)