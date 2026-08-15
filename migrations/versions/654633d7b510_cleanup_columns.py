"""cleanup_columns

Revision ID: 654633d7b510
Revises: 6eb799e90854
Create Date: 2026-08-15 21:29:16.414426

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '654633d7b510'
down_revision: Union[str, None] = '6eb799e90854'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade(engine_name: str) -> None:
    if engine_name != "archive_db":
        return
    op.drop_column('archive_reactions', 'reaction_smiles')
    op.drop_column('archive_reactions', 'mapping_source')
    op.drop_column('archive_reactions', 'dwar_rxncode')
    op.drop_column('archive_reactions', 'dwar_coordinates')

    op.drop_column('book_base', 'idcode')
    op.drop_column('book_base', 'id_coords_2d')

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

