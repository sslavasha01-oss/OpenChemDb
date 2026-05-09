"""user_journal table

Revision ID: ff659947aab5
Revises: 41101ddb15e6
Create Date: 2026-05-09 21:42:53.810447

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ff659947aab5'
down_revision: Union[str, None] = '41101ddb15e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None
from sqlalchemy.types import UserDefinedType

class MolType(UserDefinedType):
    def get_col_spec(self, **kw):
        return "MOL"

class ReactionType(UserDefinedType):
    def get_col_spec(self, **kw):
        return "REACTION"

def upgrade(engine_name: str) -> None:
    if engine_name == "users_db":  # замените на ваш engine_name
        # 1. Подключаем необходимые расширения
        op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist;")

        # 2. Создаем таблицу
        op.create_table(
            'user_journal',
            sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('external_id', sa.Integer(), nullable=False),

            sa.Column('date_added', sa.DateTime(timezone=True),
                      server_default=sa.text("TIMEZONE('UTC', CURRENT_TIMESTAMP)")),
            sa.Column('date_modified', sa.DateTime(timezone=True),
                      onupdate=sa.text("TIMEZONE('UTC', CURRENT_TIMESTAMP)")),

            # Product
            sa.Column('product_smiles', sa.Text()),
            sa.Column('product_mol_data', MolType()),
            sa.Column('product_molar_mass', sa.Numeric(precision=12, scale=4)),
            sa.Column('product_moles', sa.Numeric(precision=12, scale=6)),
            sa.Column('product_molar_ekv', sa.Numeric(precision=12, scale=4), server_default='1.0'),
            sa.Column('product_theoretical_mass', sa.Numeric(precision=12, scale=4)),
            sa.Column('product_praktical_mass', sa.Numeric(precision=12, scale=4)),
            sa.Column('product_yield_calc', sa.Numeric(precision=5, scale=2)),

            # Reactions
            sa.Column('reaction_smiles', sa.Text()),
            sa.Column('reaction_mapped_smiles', sa.Text()),
            sa.Column('reaction_mol_data', ReactionType()),  # или JSONB если нужно
            sa.Column('reaction_mol_mapped_data', ReactionType()),

            # Reagents (делаем циклом для краткости в примере, но в миграции лучше прописать явно)
            *[
                col for i in range(1, 6) for col in [
                    sa.Column(f'reagent{i}_smiles', sa.Text()),
                    sa.Column(f'reagent{i}_mol_data', MolType()),
                    sa.Column(f'reagent{i}_moles', sa.Numeric(precision=12, scale=6)),
                    sa.Column(f'reagent{i}_molar_mass', sa.Numeric(precision=12, scale=4)),
                    sa.Column(f'reagent{i}_mass', sa.Numeric(precision=12, scale=4)),
                    sa.Column(f'reagent{i}_density', sa.Numeric(precision=8, scale=4)),
                    sa.Column(f'reagent{i}_concentration', sa.Numeric(precision=5, scale=2), server_default='1.0'),
                    sa.Column(f'reagent{i}_volume', sa.Numeric(precision=12, scale=4)),
                    sa.Column(f'reagent{i}_molar_ekv', sa.Numeric(precision=12, scale=4))
                ]
            ],

            sa.Column('referenced_record_external_id', sa.Integer()),
            sa.Column('references', sa.Text()),
            sa.Column('doi', sa.Text()),
            sa.Column('procedure', sa.Text()),
        )

        # 3. Индексы
        # Составной индекс для безопасности и быстрого поиска по номеру в журнале юзера
        op.create_index('idx_user_external', 'user_journal', ['user_id', 'external_id'], unique=True)
        op.create_index('idx_date_modified', 'user_journal', ['date_modified'])

        # Multicolumn GiST индекс для химического поиска в пределах юзера
        op.execute("""
                CREATE INDEX idx_user_product_mol_gist 
                ON user_journal USING gist (user_id, product_mol_data);
            """)

        # 4. Триггер для автоинкремента external_id
        op.execute("""
                CREATE OR REPLACE FUNCTION set_external_id()
                RETURNS TRIGGER AS $$
                BEGIN
                    IF NEW.external_id IS NULL THEN
                        SELECT COALESCE(MAX(external_id), 0) + 1
                        INTO NEW.external_id
                        FROM user_journal
                        WHERE user_id = NEW.user_id;
                    END IF;
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
            """)

        op.execute("""
                CREATE TRIGGER trg_set_external_id
                BEFORE INSERT ON user_journal
                FOR EACH ROW
                EXECUTE FUNCTION set_external_id();
            """)


def downgrade(engine_name: str) -> None:
    if engine_name == "users_db":
        # Удаление триггера, функции и таблицы
        op.execute("DROP TRIGGER IF EXISTS trg_set_external_id ON user_journal;")
        op.execute("DROP FUNCTION IF EXISTS set_external_id();")
        op.drop_table('user_journal')





def upgrade_users_db() -> None:
    pass


def downgrade_users_db() -> None:
    pass


def upgrade_archive_db() -> None:
    pass


def downgrade_archive_db() -> None:
    pass

