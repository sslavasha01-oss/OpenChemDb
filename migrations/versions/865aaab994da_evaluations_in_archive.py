"""evaluations in archive

Revision ID: 865aaab994da
Revises: ff3ffc733fe3
Create Date: 2026-06-04 18:16:49.392628

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '865aaab994da'
down_revision: Union[str, None] = 'ff3ffc733fe3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade(engine_name: str) -> None:
    # Нам нужно убедиться, что миграция применяется только к users_db
    if engine_name != "archive_db":
        return

    # 1. Создаем таблицу
    op.create_table(
        'entry_evaluations',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_nickname', sa.String(length=100), nullable=False),
        sa.Column('target_table', sa.Enum('REACTIONS', 'BOOKS', 'JOURNAL', name='targettable'), nullable=False),
        sa.Column('entry_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.Enum('CHECK', 'POO', 'ERROR', name='evaluationstatus'), nullable=False),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text("TIMEZONE('UTC', CURRENT_TIMESTAMP)")),
    )

    # 2. ИНДЕКСЫ ДЛЯ СКОРОСТИ

    # Индекс для эффективного получения статусов (Batch-запросы)
    # Позволяет базе мгновенно найти все оценки для конкретной таблицы и набора ID
    op.create_index(
        'idx_eval_target_entry',
        'entry_evaluations',
        ['target_table', 'entry_id']
    )

    # Индекс для поиска всех оценок конкретного пользователя
    op.create_index(
        'idx_eval_user',
        'entry_evaluations',
        ['user_nickname']
    )

    # 3. УНИКАЛЬНОСТЬ (Один статус от одного юзера на одну запись)
    # Это также создает индекс, который ускоряет проверку при добавлении (Upsert)
    op.create_unique_constraint(
        'uq_user_target_entry',
        'entry_evaluations',
        ['user_nickname', 'target_table', 'entry_id']
    )


def downgrade(engine_name: str) -> None:
    globals()["downgrade_%s" % engine_name]()


def upgrade_users_db() -> None:
    pass


def downgrade_users_db() -> None:
    pass


def upgrade_archive_db() -> None:
    pass


def downgrade_archive_db() -> None:
    pass

