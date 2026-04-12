"""create_book_base_table

Revision ID: a17f32f54ed2
Revises: 14d5ab969d87
Create Date: 2026-03-14 19:39:47.951911

"""
from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = 'a17f32f54ed2'
down_revision: Union[str, None] = '14d5ab969d87'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy.types import UserDefinedType


class MolType(UserDefinedType):
    def get_col_spec(self, **kw):
        return "MOL"


def upgrade(engine_name: str) -> None:
    if engine_name == "archive_db":
        op.create_table(
            'book_base',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('external_id', sa.Integer(), nullable=False),
            sa.Column('name', sa.Text()),
            sa.Column('book_name', sa.Text()),
            sa.Column('pages', sa.Text()),
            sa.Column('smiles', sa.Text()),
            sa.Column('mol_data', MolType()),  # Для поиска по структуре
            sa.Column('references', sa.Text()),
            sa.Column('is_deleted', sa.Boolean(), server_default='false'),
            sa.Column('date_added', sa.DateTime(timezone=True),
                      server_default=sa.text("TIMEZONE('UTC', CURRENT_TIMESTAMP)"))
        )

        # Индекс для поиска по структурам
        op.execute("CREATE INDEX idx_book_mol_gist ON book_base USING gist (mol_data);")
        op.create_index('idx_book_external_id', 'book_base', ['external_id'])


def downgrade(engine_name: str) -> None:
    if engine_name == "archive_db":
        op.drop_table('book_base')