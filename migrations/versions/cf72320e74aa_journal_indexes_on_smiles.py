"""journal indexes on smiles

Revision ID: cf72320e74aa
Revises: e7504993ee78
Create Date: 2026-06-01 01:13:27.182100

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cf72320e74aa'
down_revision: Union[str, None] = 'e7504993ee78'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade(engine_name: str) -> None:
    if engine_name == "users_db":
        # --- 1. УДАЛЯЕМ СТАРЫЕ GIN ИНДЕКСЫ ---
        op.execute("DROP INDEX IF EXISTS idx_user_product_exact_gin;")
        for i in range(1, 6):
            op.execute(f"DROP INDEX IF EXISTS idx_user_reagent{i}_exact_gin;")

        # --- 2. СОЗДАЕМ НОВЫЕ ТЕКСТОВЫЕ GIN ИНДЕКСЫ ---
        # Индекс для точного поиска по продукту
        op.execute("""
                CREATE INDEX idx_user_product_exact_gin 
                ON user_journal USING gin (
                    user_id, 
                    (string_to_array(product_smiles, '.'))
                );
            """)

        # Индексы для точного поиска по реагентам (1-5)
        for i in range(1, 6):
            op.execute(f"""
                    CREATE INDEX idx_user_reagent{i}_exact_gin 
                    ON user_journal USING gin (
                        user_id, 
                        (string_to_array(reagent{i}_smiles, '.'))
                    );
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

