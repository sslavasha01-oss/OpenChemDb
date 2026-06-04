"""create media

Revision ID: 13e1f1592edc
Revises: 10aac137de5b
Create Date: 2026-06-04 19:53:55.494297

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '13e1f1592edc'
down_revision: Union[str, None] = '10aac137de5b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

enum_name = "attachmenttype"

def upgrade(engine_name: str) -> None:
    if engine_name != "users_db":
        return
    # 1. Добавляем новое значение в существующий Enum в Postgres (с защитой if not exists)
    op.execute(f"ALTER TYPE {enum_name} ADD VALUE IF NOT EXISTS 'MEDIA'")

    # 2. Добавляем колонку thumbnail_b64 в таблицу journal_attachment
    op.add_column('journal_attachment', sa.Column('thumbnail_b64', sa.Text(), nullable=True))


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

