"""comments and replies in archive_db

Revision ID: e31128a4a3e8
Revises: cf7e430e2834
Create Date: 2026-06-04 18:32:10.435706

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e31128a4a3e8'
down_revision: Union[str, None] = 'cf7e430e2834'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade(engine_name: str) -> None:
    if engine_name != "archive_db":
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
    )

    # Индекс для быстрого получения ответов к ветке
    op.create_index('idx_replies_comment_id', 'comment_replies', ['comment_id'])


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

