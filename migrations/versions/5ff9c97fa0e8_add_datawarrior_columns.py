"""add_datawarrior_columns

Revision ID: 5ff9c97fa0e8
Revises: 64842db946c1
Create Date: 2026-07-04 21:14:00.509908

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql.type_api import UserDefinedType

# revision identifiers, used by Alembic.
revision: str = '5ff9c97fa0e8'
down_revision: Union[str, None] = '64842db946c1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

class MolType(UserDefinedType):
    def get_col_spec(self, **kw):
        return "MOL"

def upgrade(engine_name: str) -> None:
    if engine_name != "archive_db":
        return
    op.add_column('book_base', sa.Column('idcode', sa.Text(), nullable=True))
    op.add_column('book_base', sa.Column('id_coords_2d', sa.Text(), nullable=True))
    # Добавляем колонку под полноценный моль-файл с координатами
    # Используем сырой текст выражения типа, так как в Postgres это custom type от RDKit
    op.add_column('book_base', sa.Column('mol_file', MolType(), nullable=True))


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

