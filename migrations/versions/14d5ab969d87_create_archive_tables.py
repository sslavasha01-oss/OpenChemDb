"""create_archive_tables

Revision ID: 14d5ab969d87
Revises: 4055da041f6b
Create Date: 2026-03-08 19:33:41.265553

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.types import UserDefinedType


# revision identifiers, used by Alembic.
revision: str = '14d5ab969d87'
down_revision: Union[str, None] = '4055da041f6b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

class ReactionType(UserDefinedType):
    def get_col_spec(self, **kw):
        return "REACTION"

def upgrade(engine_name: str) -> None:
    if engine_name == "archive_db":
        # 1. Расширение RDKit (если еще нет)
        op.execute("CREATE EXTENSION IF NOT EXISTS rdkit;")

        # 2. Таблица архива
        op.create_table(
            'archive_reactions',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('external_id', sa.Integer(), nullable=False),
            sa.Column('root_regno', sa.Text()),
            sa.Column('dataset_name', sa.Text()),
            sa.Column('reaction_smiles', sa.Text()),  # Исходник (строка)
            sa.Column('doi', sa.Text()),
            sa.Column('reaction_raw_smiles', sa.Text()),  # Чистая (строка)
            sa.Column('reaction_raw_data', ReactionType()),  # Чистая (RDKit)
            sa.Column('reaction_mapped_smiles', sa.Text()),  # Мапленная (строка)
            sa.Column('reaction_mapped_data', ReactionType()),  # Мапленная (RDKit)
            sa.Column('is_mapped', sa.Boolean(), default=False),
            sa.Column('mapping_source', sa.Text()),
            sa.Column('dataset_name_2', sa.Text()),
            sa.Column('rxn_regno', sa.Text()),
            sa.Column('references', sa.Text()),
            sa.Column('conditions', sa.Text()),
            sa.Column('yield_text', sa.Text()),
            sa.Column('procedure', sa.Text()),
            sa.Column('is_deleted', sa.Boolean(), server_default='false'),
            sa.Column('date_added', sa.DateTime(timezone=True),
                      server_default=sa.text("TIMEZONE('UTC', CURRENT_TIMESTAMP)"))
        )

        # 3. Индексы для химического поиска (RDKit Cartridge)
        op.execute("CREATE INDEX idx_rxn_raw_gist ON archive_reactions USING gist (reaction_raw_data);")
        op.execute("CREATE INDEX idx_rxn_mapped_gist ON archive_reactions USING gist (reaction_mapped_data);")

        # Обычные индексы для фильтрации
        op.create_index('idx_external_id', 'archive_reactions', ['external_id'])
        op.create_index('idx_doi', 'archive_reactions', ['doi'])


def downgrade(engine_name: str) -> None:
    if engine_name == "archive_db":
        op.drop_table('archive_reactions')

def upgrade_users_db() -> None:
    pass


def downgrade_users_db() -> None:
    pass


def upgrade_archive_db() -> None:
    pass


def downgrade_archive_db() -> None:
    pass

