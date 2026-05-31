"""book gin indexes on smiles

Revision ID: ff3ffc733fe3
Revises: 331c746acd51
Create Date: 2026-06-01 02:02:04.963449

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ff3ffc733fe3'
down_revision: Union[str, None] = '331c746acd51'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade(engine_name: str) -> None:
    if engine_name == "archive_db":
        # 1. Удаляем старый индекс, завязанный на функцию RDKit
        op.execute("DROP INDEX IF EXISTS idx_book_base_smiles_array_gin;")

        # 2. Создаем новый быстрый индекс по текстовому массиву
        op.execute("""
                CREATE INDEX idx_book_base_smiles_array_gin 
                ON book_base 
                USING gin (string_to_array(smiles, '.'));
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

