"""add indexes to user journal

Revision ID: 6022b14c1454
Revises: 396cc0c6f94b
Create Date: 2026-05-24 16:08:48.547390

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6022b14c1454'
down_revision: Union[str, None] = '396cc0c6f94b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade(engine_name: str) -> None:
    if engine_name == "users_db":
        # Включаем btree_gin для возможности создания составных GIN-индексов (user_id + array)
        op.execute("CREATE EXTENSION IF NOT EXISTS btree_gin;")

        # 1. Индекс для точного поиска по продукту
        op.execute("""
                CREATE INDEX idx_user_product_exact_gin 
                ON user_journal USING gin (
                    user_id, 
                    (string_to_array(mol_to_smiles(product_mol_data)::text, '.'))
                );
            """)

        # 2. Индексы для точного поиска по реагентам (1-5)
        for i in range(1, 6):
            op.execute(f"""
                    CREATE INDEX idx_user_reagent{i}_exact_gin 
                    ON user_journal USING gin (
                        user_id, 
                        (string_to_array(mol_to_smiles(reagent{i}_mol_data)::text, '.'))
                    );
                """)

        for i in range(1, 6):
            op.execute(f"""
                        CREATE INDEX idx_user_reagent{i}_mol_gist 
                        ON user_journal USING gist (
                            user_id, 
                            reagent{i}_mol_data
                        );
                    """)


def downgrade(engine_name: str) -> None:
    if engine_name == "users_db":
        # Удаляем GIN-индексы точного поиска
        op.execute("DROP INDEX IF EXISTS idx_user_product_exact_gin;")
        for i in range(1, 6):
            op.execute(f"DROP INDEX IF EXISTS idx_user_reagent{i}_exact_gin;")

        # Удаляем GiST-индексы подструктурного поиска
        for i in range(1, 6):
            op.execute(f"DROP INDEX IF EXISTS idx_user_reagent{i}_mol_gist;")





def upgrade_users_db() -> None:
    pass


def downgrade_users_db() -> None:
    pass


def upgrade_archive_db() -> None:
    pass


def downgrade_archive_db() -> None:
    pass

