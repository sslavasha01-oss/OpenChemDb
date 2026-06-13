"""add_user_id_to_evaluations

Revision ID: 192ddc7f1704
Revises: ccee402aaedf
Create Date: 2026-06-13 23:13:46.568542

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '192ddc7f1704'
down_revision: Union[str, None] = 'ccee402aaedf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade(engine_name: str) -> None:
    if engine_name != "archive_db":
        return
    op.add_column('entry_evaluations', sa.Column('user_id', sa.Integer(), nullable=False))
    # 3. Создаем индекс для user_id
    op.create_index(op.f('ix_entry_evaluations_user_id'), 'entry_evaluations', ['user_id'], unique=False)

    # 4. Пересоздаем Unique Constraint (удаляем старый по никнейму, ставим новый по ID)
    op.drop_constraint('uq_user_target_entry', 'entry_evaluations', type_='unique')
    op.create_unique_constraint('_user_entry_uc', 'entry_evaluations', ['user_id', 'target_table', 'entry_id'])


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

