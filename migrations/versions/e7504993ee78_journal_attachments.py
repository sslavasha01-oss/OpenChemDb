"""journal attachments

Revision ID: e7504993ee78
Revises: 6022b14c1454
Create Date: 2026-05-31 00:26:00.887778

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e7504993ee78'
down_revision: Union[str, None] = '6022b14c1454'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade(engine_name: str) -> None:
    if engine_name != "users_db":
        return
    op.create_table(
        'journal_attachment',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        # Замени 'user_journal.id' на реальное имя таблицы твоего журнала, если оно отличается
        sa.Column('journal_record_id', sa.Integer(), sa.ForeignKey('user_journal.id', ondelete='CASCADE'),
                  nullable=False),
        sa.Column('type', sa.Enum('ARTICLE', 'SPECTRUM', name='attachmenttype'), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('file_path', sa.String(length=1000), nullable=False),
        sa.Column('date_added', sa.DateTime(), server_default=sa.func.now(), nullable=False)
    )


def downgrade(engine_name: str) -> None:
    if engine_name != "users_db":
        return
    op.drop_table('journal_attachment')


def upgrade_users_db() -> None:
    pass


def downgrade_users_db() -> None:
    pass


def upgrade_archive_db() -> None:
    pass


def downgrade_archive_db() -> None:
    pass

