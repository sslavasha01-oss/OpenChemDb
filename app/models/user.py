from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import String, Boolean, Integer, BigInteger, DateTime, ForeignKey, JSON, Numeric
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
    billing_email: Mapped[Optional[str]] = mapped_column(String, unique=True, index=True, nullable=True)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, default="USER", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    attachments_total_size: Mapped[int] = mapped_column(BigInteger, server_default="0", default=0, nullable=False)
    tariff_plan: Mapped[str] = mapped_column(String(50), server_default="FREE", default="FREE", nullable=False)
    subscription_period_end: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class Webhook(Base):
    __tablename__ = "webhooks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    event_type: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    supporter_email: Mapped[str] = mapped_column(String, index=True, nullable=False)
    supporter_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False)

    current_period_start: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    current_period_end: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    raw_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Ссылка на пользователя (null, если не сматчили)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)