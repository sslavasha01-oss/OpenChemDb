"""exports_table_add_status

Revision ID: 631abf7fee0f
Revises: 0ba25ede5d49
Create Date: 2026-06-05 01:48:52.322812

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '631abf7fee0f'
down_revision: Union[str, None] = '0ba25ede5d49'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade(engine_name: str) -> None:
    if engine_name != 'users_db':
        return
    # 1. Объявляем имя нового типа ENUM для PostgreSQL
    process_status_enum = sa.Enum(
        'PROCESSING_EXPORT',
        'PROCESSING_IMPORT',
        'COMPLETED',
        'FAILED',
        name='processstatus'
    )

    # 2. Создаем тип ENUM в базе данных перед добавлением колонки
    process_status_enum.create(op.get_bind(), checkfirst=True)

    # 3. Добавляем новые колонки в существующую таблицу exports
    op.add_column('exports', sa.Column('status', process_status_enum, nullable=True))
    op.add_column('exports', sa.Column('error_message', sa.String(), nullable=True))


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

