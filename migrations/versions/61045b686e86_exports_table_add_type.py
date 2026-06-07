"""exports_table_add_type

Revision ID: 61045b686e86
Revises: 631abf7fee0f
Create Date: 2026-06-07 18:53:52.599213

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '61045b686e86'
down_revision: Union[str, None] = '631abf7fee0f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade(engine_name: str) -> None:
    if engine_name != 'users_db':
        return

    op.drop_constraint('exports_user_id_key', 'exports', type_='unique')

    # 1. Объявляем имя нового типа ENUM для PostgreSQL
    process_type_enum = sa.Enum(
        'EXPORT',
        'IMPORT',
        name='processtype'
    )



    # 2. Создаем тип ENUM в базе данных перед добавлением колонки
    process_type_enum.create(op.get_bind(), checkfirst=True)

    # 3. Добавляем новые колонки в существующую таблицу exports
    op.add_column('exports', sa.Column('type', process_type_enum, nullable=True))

    op.create_unique_constraint(
        'uq_exports_user_id_type',  # Имя нового ограничения
        'exports',  # Имя таблицы
        ['user_id', 'type']  # Список колонок
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

