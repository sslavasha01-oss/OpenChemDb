"""evaluations in archive add updated at

Revision ID: cf7e430e2834
Revises: 865aaab994da
Create Date: 2026-06-04 18:27:56.214059

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cf7e430e2834'
down_revision: Union[str, None] = '865aaab994da'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade(engine_name: str) -> None:
    if engine_name != "archive_db":
        return
    # Добавляем колонки с дефолтным значением "сейчас"
    op.add_column('entry_evaluations',
                  sa.Column('updated_at', sa.DateTime(timezone=True),
                            server_default=sa.text("TIMEZONE('utc', CURRENT_TIMESTAMP)"), nullable=True)
                  )
    # Индекс для сортировки по дате (чтобы быстро видеть последние "какашки")
    op.create_index('idx_eval_created_at', 'entry_evaluations', ['created_at'])


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

