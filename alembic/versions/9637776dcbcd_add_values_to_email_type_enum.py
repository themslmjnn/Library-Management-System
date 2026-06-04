"""add_values_to_email_type_enum

Revision ID: 9637776dcbcd
Revises: 978eb65ebf9f
Create Date: 2026-06-04 10:22:10.250356

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9637776dcbcd"
down_revision: Union[str, Sequence[str], None] = "978eb65ebf9f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TYPE emailtype ADD VALUE 'account_deactivation'")
    op.execute("ALTER TYPE emailtype ADD VALUE 'account_activation'")
    op.execute("ALTER TYPE emailtype ADD VALUE 'admin_email_override'")


def downgrade() -> None:
    """Downgrade schema."""
    pass
