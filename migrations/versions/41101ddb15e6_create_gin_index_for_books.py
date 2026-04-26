"""create gin index for books

Revision ID: 41101ddb15e6
Revises: 8e08e71b6abd
Create Date: 2026-04-19 16:42:09.161450

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '41101ddb15e6'
down_revision: Union[str, None] = '8e08e71b6abd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade(engine_name: str) -> None:
    if engine_name == "archive_db":
        op.execute("""
                CREATE INDEX IF NOT EXISTS idx_book_base_smiles_array_gin 
                ON book_base 
                USING gin (string_to_array(mol_to_smiles(mol_data)::text, '.'));
            """)


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

