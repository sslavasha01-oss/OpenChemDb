"""add_datawarrior_fields_to_journal

Revision ID: 15f96a4b4058
Revises: 0afc2afc50bd
Create Date: 2026-07-05 02:02:30.597879

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '15f96a4b4058'
down_revision: Union[str, None] = '0afc2afc50bd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade(engine_name: str) -> None:
    if engine_name != "archive_db":
        return
    # Добавляем 3 текстовые колонки в таблицу archive_reactions
    op.add_column('archive_reactions', sa.Column('dwar_rxncode', sa.Text(), nullable=True))
    op.add_column('archive_reactions', sa.Column('dwar_coordinates', sa.Text(), nullable=True))
    op.add_column('archive_reactions', sa.Column('raw_rxn_file', sa.Text(), nullable=True))


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

