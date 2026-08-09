"""add_names_and_trgm_indexes_to_user_journal

Revision ID: 4a6f9f151027
Revises: 15f96a4b4058
Create Date: 2026-08-09 11:23:22.183856

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4a6f9f151027'
down_revision: Union[str, None] = '15f96a4b4058'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade(engine_name: str) -> None:
    if engine_name != "users_db":
        return
    # 1. Включаем расширение pg_trgm для поиска по подстрокам (триграммам)
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")

    # 2. Добавляем новые колонки
    op.add_column('user_journal', sa.Column('product_name', sa.Text(), nullable=True))
    for i in range(1, 6):
        op.add_column('user_journal', sa.Column(f'reagent{i}_name', sa.Text(), nullable=True))

    # 3. Индекс для названия продукта (user_id + product_name с gin_trgm_ops)
    op.execute("""
        CREATE INDEX idx_user_product_name_trgm 
        ON public.user_journal 
        USING gin (user_id, product_name public.gin_trgm_ops);
    """)

    # 4. Составные/индивидуальные индексы для названий реагентов
    for i in range(1, 6):
        op.execute(f"""
            CREATE INDEX idx_user_reagent{i}_name_trgm 
            ON public.user_journal 
            USING gin (user_id, reagent{i}_name public.gin_trgm_ops);
        """)


def downgrade(engine_name: str) -> None:
    if engine_name != "users_db":
        return
    # Удаляем индексы
    op.execute("DROP INDEX IF EXISTS public.idx_user_product_name_trgm;")
    for i in range(1, 6):
        op.execute(f"DROP INDEX IF EXISTS public.idx_user_reagent{i}_name_trgm;")

    # Удаляем колонки
    for i in range(1, 6):
        op.drop_column('user_journal', f'reagent{i}_name')
    op.drop_column('user_journal', 'product_name')





def upgrade_users_db() -> None:
    pass


def downgrade_users_db() -> None:
    pass


def upgrade_archive_db() -> None:
    pass


def downgrade_archive_db() -> None:
    pass

