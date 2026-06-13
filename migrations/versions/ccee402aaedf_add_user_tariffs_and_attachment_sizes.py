"""add_user_tariffs_and_attachment_sizes

Revision ID: ccee402aaedf
Revises: 61045b686e86
Create Date: 2026-06-13 19:15:46.606617

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ccee402aaedf'
down_revision: Union[str, None] = '61045b686e86'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade(engine_name: str) -> None:
    if engine_name != "users_db":
        return
    # 1. Добавляем колонки в таблицу users
    op.add_column('users', sa.Column('attachments_total_size', sa.BigInteger(), server_default='0', nullable=False))
    op.add_column('users', sa.Column('tariff_plan', sa.String(length=50), server_default='FREE', nullable=False))

    # 2. Добавляем колонку в таблицу journal_attachment
    op.add_column('journal_attachment', sa.Column('file_size', sa.BigInteger(), server_default='0', nullable=False))


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

