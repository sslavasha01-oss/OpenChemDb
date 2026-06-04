"""comment reactions in archive_db

Revision ID: 346773943bc5
Revises: e31128a4a3e8
Create Date: 2026-06-04 18:34:34.770523

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '346773943bc5'
down_revision: Union[str, None] = 'e31128a4a3e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade(engine_name: str) -> None:
    if engine_name != "archive_db":
        return
    # 2. Создаем таблицу
    op.create_table(
        'comment_reactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('target_type', sa.Enum('COMMENT', 'REPLY', name='reaction_target_type'), nullable=False),
        sa.Column('target_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('reaction_type', sa.Enum('USEFUL', 'NOT_USEFUL', name='reaction_type'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('target_type', 'target_id', 'user_id', name='idx_unique_user_reaction')
    )

    op.create_index(op.f('ix_comment_reactions_id'), 'comment_reactions', ['id'], unique=False)
    op.create_index(op.f('ix_comment_reactions_target_id'), 'comment_reactions', ['target_id'], unique=False)


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

