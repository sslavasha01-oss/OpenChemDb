"""add_raw_molfile

Revision ID: 0afc2afc50bd
Revises: 5ff9c97fa0e8
Create Date: 2026-07-04 23:57:39.523649

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0afc2afc50bd'
down_revision: Union[str, None] = '5ff9c97fa0e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade(engine_name: str) -> None:
    if engine_name != "archive_db":
        return
    op.add_column('book_base', sa.Column('mol_file_raw', sa.Text(), nullable=True))


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

