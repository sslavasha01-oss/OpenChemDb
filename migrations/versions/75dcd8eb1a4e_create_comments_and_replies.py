"""create_comments_and_replies

Revision ID: 75dcd8eb1a4e
Revises: 0a96424844ba
Create Date: 2026-03-15 17:45:11.593757

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '75dcd8eb1a4e'
down_revision: Union[str, None] = '0a96424844ba'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade(engine_name : str) -> None:
    if engine_name != "users_db":
        return
    # 1. Таблица основных комментариев
    op.create_table(
        'comments',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('target_table',
                  sa.Enum('REACTIONS', 'BOOKS', 'JOURNAL', name='comment_target'), nullable=False),
        sa.Column('entry_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('user_nickname', sa.String(length=100), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text("TIMEZONE('utc', CURRENT_TIMESTAMP)")),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text("TIMEZONE('utc', CURRENT_TIMESTAMP)")),

        # Внешний ключ на таблицу пользователей
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )

    # Индексы для быстрого поиска комментариев к конкретной записи
    op.create_index('idx_comments_target_entry', 'comments', ['target_table', 'entry_id'])
    op.create_index('idx_comments_created_at', 'comments', ['created_at'])

    # 2. Таблица ответов на комментарии (Replies)
    op.create_table(
        'comment_replies',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('comment_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('user_nickname', sa.String(length=100), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text("TIMEZONE('utc', CURRENT_TIMESTAMP)")),

        # Каскадное удаление: если удален основной комментарий, ответы тоже удаляются
        sa.ForeignKeyConstraint(['comment_id'], ['comments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )

    # Индекс для быстрого получения ответов к ветке
    op.create_index('idx_replies_comment_id', 'comment_replies', ['comment_id'])


def downgrade(engine_name : str) -> None:
    if engine_name != "users_db":
        return
    op.drop_table('comment_replies')
    op.drop_table('comments')

