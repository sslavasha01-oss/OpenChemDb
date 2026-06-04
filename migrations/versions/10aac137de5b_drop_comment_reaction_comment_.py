"""drop comment reaction comment evaluation from user_db

Revision ID: 10aac137de5b
Revises: 346773943bc5
Create Date: 2026-06-04 18:41:54.322260

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '10aac137de5b'
down_revision: Union[str, None] = '346773943bc5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade(engine_name: str) -> None:
    if engine_name != "users_db":
        return
    op.drop_table("comment_reactions")
    op.drop_table("comment_replies")
    op.drop_table("comments")
    op.drop_table("entry_evaluations")


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

