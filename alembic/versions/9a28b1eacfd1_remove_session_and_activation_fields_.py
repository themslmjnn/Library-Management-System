"""Remove session and activation fields from users table

Revision ID: 9a28b1eacfd1
Revises: cd753ce2681a
Create Date: 2026-05-14 11:16:24.900246

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '9a28b1eacfd1'
down_revision: Union[str, Sequence[str], None] = 'cd753ce2681a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column("users", "access_token_version")
    op.drop_column("users", "refresh_token_hash")
    op.drop_column("users", "refresh_token_expires_at")
    op.drop_column("users", "refresh_token_family")
    op.drop_column("users", "failed_login_attempts")
    op.drop_column("users", "locked_until")
    op.drop_column("users", "invite_token_hash")
    op.drop_column("users", "invite_token_expires_at")
    op.drop_column("users", "account_activation_code_hash")
    op.drop_column("users", "account_activation_code_expires_at")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        "users",
        sa.Column("invite_token_hash", sa.String(), nullable=True)
    )
    op.add_column(
        "users",
        sa.Column("invite_token_expires_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "users",
        sa.Column("access_token_version", sa.Integer(), nullable=False)
    )
    op.add_column(
        "users",
        sa.Column("refresh_token_hash", sa.String(), nullable=True)
    )
    op.add_column(
        "users",
        sa.Column(
            "refresh_token_expires_at", sa.DateTime(timezone=True), nullable=True
        ),
    )
    op.add_column(
        "users", sa.Column("refresh_token_family", sa.String(length=64), nullable=True)
    )
    op.add_column(
        "users", sa.Column("failed_login_attempts", sa.Integer(), nullable=False)
    )
    op.add_column(
        "users", sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True)
    )

    op.add_column(
        "users", sa.Column("account_activation_code_hash", sa.String(), nullable=True)
    )
    op.add_column(
        "users",
        sa.Column(
            "account_activation_code_expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
