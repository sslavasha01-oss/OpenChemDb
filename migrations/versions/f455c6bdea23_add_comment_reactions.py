"""add_comment_reactions

Revision ID: f455c6bdea23
Revises: 75dcd8eb1a4e
Create Date: 2026-03-15 20:28:05.971701

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'f455c6bdea23'
down_revision: Union[str, None] = '75dcd8eb1a4e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade(engine_name : str) -> None:
    if engine_name != "users_db":
        return
    # 2. Создаем таблицу
    op.create_table(
        'comment_reactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('target_type', sa.Enum('COMMENT', 'REPLY', name='reaction_target_type'), nullable=False),
        sa.Column('target_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('reaction_type', sa.Enum('USEFUL', 'NOT_USEFUL', name='reaction_type'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('target_type', 'target_id', 'user_id', name='idx_unique_user_reaction')
    )

    op.create_index(op.f('ix_comment_reactions_id'), 'comment_reactions', ['id'], unique=False)
    op.create_index(op.f('ix_comment_reactions_target_id'), 'comment_reactions', ['target_id'], unique=False)

def downgrade(engine_name : str):
    if engine_name != "users_db":
        return
    # Удаляем таблицу
    op.drop_table('comment_reactions')

    # Удаляем типы
    op.execute("DROP TYPE reaction_target_type;")
    op.execute("DROP TYPE reaction_type;")
