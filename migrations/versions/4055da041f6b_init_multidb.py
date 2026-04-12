"""init_multidb

Revision ID: 4055da041f6b
Revises: 
Create Date: 2026-03-01 20:05:39.621799

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4055da041f6b'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade(engine_name: str) -> None:
    if engine_name == "users_db":
        upgrade_users_db()
    elif engine_name == "archive_db":
        upgrade_archive_db()

def downgrade(engine_name: str) -> None:
    if engine_name == "users_db":
        downgrade_users_db()
    elif engine_name == "archive_db":
        downgrade_archive_db()

def upgrade_users_db() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS rdkit;")
    op.execute("""
        CREATE TABLE users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(255) UNIQUE NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            hashed_password VARCHAR(255) NOT NULL,
            role VARCHAR(50) NOT NULL DEFAULT 'USER',
            is_active BOOLEAN DEFAULT TRUE
        );
    """)


def upgrade_archive_db() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS rdkit;")

def downgrade_users_db() -> None:
    op.execute("DROP TABLE users;")

def downgrade_archive_db() -> None:
    pass

