"""add_timestamps_to_evaluations

Revision ID: 0a96424844ba
Revises: d0c214e71ebd
Create Date: 2026-03-15 16:27:19.802448

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0a96424844ba'
down_revision: Union[str, None] = 'd0c214e71ebd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade(engine_name : str) -> None:
    if engine_name != "users_db":
        return
    # Добавляем колонки с дефолтным значением "сейчас"
    op.add_column('entry_evaluations',
        sa.Column('updated_at', sa.DateTime(timezone=True),
        server_default=sa.text("TIMEZONE('utc', CURRENT_TIMESTAMP)"), nullable=True)
    )
    # Индекс для сортировки по дате (чтобы быстро видеть последние "какашки")
    op.create_index('idx_eval_created_at', 'entry_evaluations', ['created_at'])

def downgrade(engine_name : str) -> None:
    if engine_name != "users_db":
        return
    op.drop_index('idx_eval_created_at', table_name='entry_evaluations')
    op.drop_column('entry_evaluations', 'updated_at')