"""add_user_journal_full_text_search

Revision ID: 6eb799e90854
Revises: 030e69e9163e
Create Date: 2026-08-09 16:06:45.817146

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6eb799e90854'
down_revision: Union[str, None] = '030e69e9163e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade(engine_name: str) -> None:
    if engine_name != "users_db":
        return
    op.execute('DROP INDEX IF EXISTS public.idx_user_procedure_trgm;')

    # 2. Создаем GIN-индекс с конфигурацией 'simple'
    op.execute(
        """
        CREATE INDEX idx_user_procedure_fts 
        ON public.user_journal 
        USING gin (user_id, to_tsvector('simple', "procedure"));
        """
    )


def downgrade(engine_name: str) -> None:
    if engine_name != "users_db":
        return
    op.execute('DROP INDEX IF EXISTS public.idx_user_procedure_fts;')

    op.execute(
        'CREATE INDEX idx_user_procedure_trgm ON public.user_journal USING gin (user_id, "procedure" gin_trgm_ops);'
    )





def upgrade_users_db() -> None:
    pass


def downgrade_users_db() -> None:
    pass


def upgrade_archive_db() -> None:
    pass


def downgrade_archive_db() -> None:
    pass

