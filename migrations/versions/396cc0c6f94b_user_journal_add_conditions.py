"""user_journal add conditions

Revision ID: 396cc0c6f94b
Revises: ff659947aab5
Create Date: 2026-05-09 23:45:25.991820

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '396cc0c6f94b'
down_revision: Union[str, None] = 'ff659947aab5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade(engine_name: str) -> None:
    if engine_name == "users_db":
        op.add_column('user_journal', sa.Column('conditions', sa.Text(), nullable=True))


def downgrade(engine_name: str) -> None:
    if engine_name == "users_db":
        op.drop_column('user_journal', 'conditions')



def upgrade_users_db() -> None:
    pass


def downgrade_users_db() -> None:
    pass


def upgrade_archive_db() -> None:
    pass


def downgrade_archive_db() -> None:
    pass

