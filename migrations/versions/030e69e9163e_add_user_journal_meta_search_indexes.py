"""add_user_journal_meta_search_indexes

Revision ID: 030e69e9163e
Revises: 4a6f9f151027
Create Date: 2026-08-09 14:50:42.862555

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '030e69e9163e'
down_revision: Union[str, None] = '4a6f9f151027'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade(engine_name: str) -> None:
    if engine_name != "users_db":
        return
    # GIN trgm индексы для поиска по подстроке (ILIKE) с учетом user_id
    op.execute(
        "CREATE INDEX idx_user_conditions_trgm ON public.user_journal USING gin (user_id, conditions gin_trgm_ops);"
    )
    op.execute(
        'CREATE INDEX idx_user_references_trgm ON public.user_journal USING gin (user_id, "references" gin_trgm_ops);'
    )
    op.execute(
        'CREATE INDEX idx_user_procedure_trgm ON public.user_journal USING gin (user_id, "procedure" gin_trgm_ops);'
    )

    # B-tree индекс для точного совпадения по DOI с учетом user_id
    op.create_index(
        'idx_user_doi',
        'user_journal',
        ['user_id', 'doi'],
        unique=False,
        postgresql_using='btree'
    )


def downgrade(engine_name: str) -> None:
    if engine_name != "users_db":
        return
    op.drop_index('idx_user_doi', table_name='user_journal')
    op.execute('DROP INDEX IF EXISTS public.idx_user_procedure_trgm;')
    op.execute('DROP INDEX IF EXISTS public.idx_user_references_trgm;')
    op.execute('DROP INDEX IF EXISTS public.idx_user_conditions_trgm;')





def upgrade_users_db() -> None:
    pass


def downgrade_users_db() -> None:
    pass


def upgrade_archive_db() -> None:
    pass


def downgrade_archive_db() -> None:
    pass

