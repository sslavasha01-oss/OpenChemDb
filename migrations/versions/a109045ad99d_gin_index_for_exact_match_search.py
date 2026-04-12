"""gin index for exact match search

Revision ID: a109045ad99d
Revises: bb1bf942c745
Create Date: 2026-04-12 13:05:33.097413

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a109045ad99d'
down_revision: Union[str, None] = 'bb1bf942c745'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade(engine_name: str) -> None:
    if engine_name == "archive_db":
        op.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_gin_reactants_components 
            ON archive_reactions 
            USING GIN (string_to_array(mol_to_smiles(mol_reactants)::text, '.'));
            """
        )

        # 2. Создаем индекс для продуктов
        op.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_gin_products_components 
            ON archive_reactions 
            USING GIN (string_to_array(mol_to_smiles(mol_products)::text, '.'));
            """
        )


def downgrade(engine_name: str) -> None:
    if engine_name == "archive_db":
        op.drop_index('idx_gin_reactants_components', table_name='archive_reactions')
        op.drop_index('idx_gin_products_components', table_name='archive_reactions')





def upgrade_users_db() -> None:
    pass


def downgrade_users_db() -> None:
    pass


def upgrade_archive_db() -> None:
    pass


def downgrade_archive_db() -> None:
    pass

