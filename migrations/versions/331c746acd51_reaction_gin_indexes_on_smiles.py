"""reaction gin indexes on smiles

Revision ID: 331c746acd51
Revises: cf72320e74aa
Create Date: 2026-06-01 01:32:02.535525

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '331c746acd51'
down_revision: Union[str, None] = 'cf72320e74aa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade(engine_name: str) -> None:
    if engine_name == "archive_db":
        # 1. УДАЛЯЕМ СТАРЫЕ GIN ИНДЕКСЫ, КОТОРЫЕ ИСПОЛЬЗОВАЛИ ФУНКЦИЮ RDKit
        op.drop_index('idx_gin_reactants_from_rxn', table_name='archive_reactions')
        op.drop_index('idx_gin_products_from_rxn', table_name='archive_reactions')

        # 2. СОЗДАЕМ НОВЫЕ ТЕКСТОВЫЕ GIN ИНДЕКСЫ НА БАЗЕ reaction_raw_smiles

        # Индекс для Реагентов (первая часть до >>)
        op.execute(
            """
            CREATE INDEX idx_gin_reactants_from_smiles 
            ON archive_reactions 
            USING GIN (
                string_to_array(
                    split_part(reaction_raw_smiles, '>', 1), 
                    '.'
                )
            );
            """
        )

        # Индекс для Продуктов (последняя часть после >>)
        op.execute(
            """
            CREATE INDEX idx_gin_products_from_smiles 
            ON archive_reactions 
            USING GIN (
                string_to_array(
                    split_part(reaction_raw_smiles, '>', 3), 
                    '.'
                )
            );
            """
        )


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

