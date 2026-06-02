"""add activation_with_code email type

Revision ID: 978eb65ebf9f
Revises: aca7199476cd
Create Date: 2026-06-02 10:06:39.037256

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '978eb65ebf9f'
down_revision: Union[str, Sequence[str], None] = 'aca7199476cd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        "ALTER TYPE emailtype ADD VALUE 'activation_with_code'"
    )


def downgrade() -> None:
    """Downgrade schema."""
    pass
