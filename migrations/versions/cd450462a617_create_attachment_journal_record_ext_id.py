"""create attachment journal_record_ext_id

Revision ID: cd450462a617
Revises: 13e1f1592edc
Create Date: 2026-06-04 22:04:55.743225

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cd450462a617'
down_revision: Union[str, None] = '13e1f1592edc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade(engine_name: str) -> None:
    if engine_name != "users_db":
        return
    op.add_column('journal_attachment',
                  sa.Column('journal_record_ext_id', sa.Integer()))


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

