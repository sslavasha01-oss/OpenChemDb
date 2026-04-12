"""clean database optimize gin index

Revision ID: 8e08e71b6abd
Revises: a109045ad99d
Create Date: 2026-04-12 15:23:09.403967

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8e08e71b6abd'
down_revision: Union[str, None] = 'a109045ad99d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade(engine_name: str) -> None:
    if engine_name == "archive_db":
        # 1. Удаляем старые индексы и колонки (как планировали)
        op.drop_index('idx_gin_reactants_components', table_name='archive_reactions')
        op.drop_index('idx_gin_products_components', table_name='archive_reactions')
        op.drop_column('archive_reactions', 'mol_reactants')
        op.drop_column('archive_reactions', 'mol_products')

        # 2. Создаем новые индексы, парся SMILES реакции
        # split_part(строка, разделитель, номер_части)

        # Индекс для Реагентов (первая часть до >>)
        op.execute(
            """
            CREATE INDEX idx_gin_reactants_from_rxn 
            ON archive_reactions 
            USING GIN (
                string_to_array(
                    split_part(reaction_to_smiles(reaction_raw_data)::text, '>', 1), 
                    '.'
                )
            );
            """
        )

        # Индекс для Продуктов (последняя часть после >>)
        op.execute(
            """
            CREATE INDEX idx_gin_products_from_rxn 
            ON archive_reactions 
            USING GIN (
                string_to_array(
                    split_part(reaction_to_smiles(reaction_raw_data)::text, '>', 3), 
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

