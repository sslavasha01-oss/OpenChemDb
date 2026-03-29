import enum
from sqlalchemy import Column, Integer, String, Enum, DateTime, UniqueConstraint, text
from app.core.db import Base  # Твой базовый класс моделей


class EvaluationStatus(str, enum.Enum):
    CHECK = "CHECK"  # Воспроизведено
    POO = "POO"  # Не воспроизводится (Плохо)
    ERROR = "ERROR"  # Ошибка в данных/структуре


class TargetTable(str, enum.Enum):
    REACTIONS = "REACTIONS"
    BOOKS = "BOOKS"
    JOURNAL = "JOURNAL"


class EntryEvaluation(Base):
    __tablename__ = "entry_evaluations"

    id = Column(Integer, primary_key=True, index=True)
    user_nickname = Column(String, nullable=False, index=True)

    # ID записи в соответствующей таблице
    entry_id = Column(Integer, nullable=False, index=True)

    target_table = Column(
        Enum(TargetTable, native_enum=True),
        nullable=False
    )
    status = Column(
        Enum(EvaluationStatus, native_enum=True, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False
    )

    comment = Column(String, nullable=True)  # Опционально: почему ошибка

    # Дата создания — ставится один раз
    created_at = Column(
        DateTime(timezone=True),
        server_default=text("TIMEZONE('utc', CURRENT_TIMESTAMP)"),
        index=True  # Индекс важен для сортировки в админке
    )

    # Дата обновления — меняется при каждом сохранении
    updated_at = Column(
        DateTime(timezone=True),
        server_default=text("TIMEZONE('utc', CURRENT_TIMESTAMP)"),
        onupdate=text("TIMEZONE('utc', CURRENT_TIMESTAMP)")
    )
    # Ограничение: один пользователь — одна реакция на конкретную запись
    __table_args__ = (
        UniqueConstraint('user_nickname', 'target_table', 'entry_id', name='_user_entry_uc'),
    )