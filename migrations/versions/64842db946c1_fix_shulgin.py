"""fix shulgin

Revision ID: 64842db946c1
Revises: 55ef541bf840
Create Date: 2026-06-28 21:43:00.717723

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '64842db946c1'
down_revision: Union[str, None] = '55ef541bf840'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade(engine_name: str) -> None:
    if engine_name != "archive_db":
        return
    op.execute(
        """
        update book_base set book_name = 'SOP/Sulgin Phenethylamines i Have Known And Loved A Chemical Lov' where
        book_name = 'SOP/Sulgin Phenethylamines i Have Known And Loved A Chemical Lov.pdf';
        update book_base set book_name = 'SOP/Sulgin Tryptamines i Have Known And Loved The Chemistry Cont' where
        book_name = 'SOP/Sulgin Tryptamines i Have Known And Loved The Chemistry Cont.pdf';
        """
    )


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

