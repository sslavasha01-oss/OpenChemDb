"""add_user_id_fk_to_journal

Revision ID: 6da9d3a982e2
Revises: 192ddc7f1704
Create Date: 2026-06-14 17:22:06.094341

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6da9d3a982e2'
down_revision: Union[str, None] = '192ddc7f1704'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade(engine_name: str) -> None:
    if engine_name != "users_db":
        return
    op.create_foreign_key(
        'fk_user_journal_user_id_users',  # Имя устанавливаемого индекса/ограничения
        'user_journal',  # Таблица, куда добавляем FK
        'users',  # Таблица, на которую ссылаемся (проверь имя!)
        ['user_id'],  # Локальная колонка
        ['id'],  # Удаленная колонка
        ondelete='CASCADE'  # Каскадное удаление (если добавил в модель)
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

