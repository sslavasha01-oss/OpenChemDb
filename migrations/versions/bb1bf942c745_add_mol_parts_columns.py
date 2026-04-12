"""add_mol_parts_columns

Revision ID: bb1bf942c745
Revises: f455c6bdea23
Create Date: 2026-04-11 23:44:11.245401

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bb1bf942c745'
down_revision: Union[str, None] = 'f455c6bdea23'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade(engine_name: str) -> None:
    if engine_name == "archive_db":
        # 1. Добавляем колонки для реагентов и продуктов
        # Используем op.execute, так как тип mol специфичен для RDKit
        op.execute("ALTER TABLE archive_reactions ADD COLUMN mol_reactants mol")
        op.execute("ALTER TABLE archive_reactions ADD COLUMN mol_products mol")

        # 2. Создаем GIST индексы для быстрого поиска
        # Мы используем CONCURRENTLY, если база живая, но для Alembic в upgrade
        # обычно пишем стандартно. На 3 млн записей создание индексов займет 5-10 минут.
        op.execute("CREATE INDEX idx_archive_res_reactants_mol ON archive_reactions USING GIST (mol_reactants)")
        op.execute("CREATE INDEX idx_archive_res_products_mol ON archive_reactions USING GIST (mol_products)")


def downgrade(engine_name: str) -> None:
    if engine_name == "archive_db":
        # Удаляем индексы
        op.drop_index('idx_archive_res_products_mol', table_name='archive_reactions')
        op.drop_index('idx_archive_res_reactants_mol', table_name='archive_reactions')

        # Удаляем колонки
        op.drop_column('archive_reactions', 'mol_products')
        op.drop_column('archive_reactions', 'mol_reactants')


def upgrade_users_db() -> None:
    pass


def downgrade_users_db() -> None:
    pass


def upgrade_archive_db() -> None:
    pass


def downgrade_archive_db() -> None:
    pass

