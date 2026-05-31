"""create_updated_at_triggers

Revision ID: cb29eb887844
Revises: 248f8633b07a
Create Date: 2026-05-31 21:20:58.795818

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cb29eb887844'
down_revision: Union[str, Sequence[str], None] = '248f8633b07a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create the shared trigger function once
    op.execute("""
        CREATE OR REPLACE FUNCTION set_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    tables = [
        "users",
        "users_sessions",
        "users_activation",
        "books",
        "inventories",
        "loans",
    ]

    for table in tables:
        op.execute(f"""
            CREATE TRIGGER set_updated_at_{table}
            BEFORE UPDATE ON {table}
            FOR EACH ROW
            EXECUTE FUNCTION set_updated_at();
        """)


def downgrade() -> None:
    tables = [
        "users",
        "users_sessions",
        "users_activation",
        "books",
        "inventories",
        "loans",
    ]

    for table in tables:
        op.execute(
            f"DROP TRIGGER IF EXISTS set_updated_at_{table} ON {table};"
        )

    op.execute("DROP FUNCTION IF EXISTS set_updated_at;")
