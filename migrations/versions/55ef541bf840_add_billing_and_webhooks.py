"""add_billing_and_webhooks

Revision ID: 55ef541bf840
Revises: 6da9d3a982e2
Create Date: 2026-06-21 21:46:10.197817

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '55ef541bf840'
down_revision: Union[str, None] = '6da9d3a982e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade(engine_name: str) -> None:
    if engine_name != "users_db":
        return
    # 1. Обновляем таблицу users (добавляем новые колонки)
    op.add_column('users', sa.Column('billing_email', sa.String(), nullable=True))
    op.add_column('users', sa.Column('subscription_period_end', sa.DateTime(), nullable=True))
    op.create_index(op.f('ix_users_billing_email'), 'users', ['billing_email'], unique=True)

    # 2. Создаем новую таблицу webhooks
    op.create_table('webhooks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('supporter_email', sa.String(), nullable=False),
        sa.Column('supporter_name', sa.String(), nullable=True),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=10), nullable=False),
        sa.Column('current_period_start', sa.DateTime(), nullable=True),
        sa.Column('current_period_end', sa.DateTime(), nullable=True),
        sa.Column('raw_payload', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_webhooks_event_type'), 'webhooks', ['event_type'], unique=False)
    op.create_index(op.f('ix_webhooks_id'), 'webhooks', ['id'], unique=False)
    op.create_index(op.f('ix_webhooks_supporter_email'), 'webhooks', ['supporter_email'], unique=False)


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

