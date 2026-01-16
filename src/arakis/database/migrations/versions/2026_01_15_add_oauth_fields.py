"""Add OAuth authentication fields

Revision ID: e9b6f7c8d0f3
Revises: d8a5f6b7c9e2
Create Date: 2026-01-15 10:00:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e9b6f7c8d0f3"
down_revision: Union[str, Sequence[str], None] = "d8a5f6b7c9e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add OAuth fields."""
    # Add OAuth fields to users table
    op.add_column("users", sa.Column("apple_id", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("google_id", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("avatar_url", sa.String(length=1000), nullable=True))
    op.add_column("users", sa.Column("email_verified", sa.Boolean(), nullable=True, default=False))
    op.add_column(
        "users", sa.Column("auth_provider", sa.String(length=20), nullable=True, default="email")
    )

    # Make hashed_password nullable for OAuth-only users
    op.alter_column("users", "hashed_password", nullable=True)

    # Create indexes for OAuth provider IDs
    op.create_index(op.f("ix_users_apple_id"), "users", ["apple_id"], unique=True)
    op.create_index(op.f("ix_users_google_id"), "users", ["google_id"], unique=True)

    # Add session_id to workflows for trial tracking
    op.add_column("workflows", sa.Column("session_id", sa.String(length=64), nullable=True))
    op.create_index(op.f("ix_workflows_session_id"), "workflows", ["session_id"], unique=False)

    # Create refresh_tokens table
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("device_info", sa.String(length=255), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_refresh_tokens_token_hash"), "refresh_tokens", ["token_hash"], unique=False)


def downgrade() -> None:
    """Downgrade schema - remove OAuth fields."""
    # Drop refresh_tokens table
    op.drop_index(op.f("ix_refresh_tokens_token_hash"), table_name="refresh_tokens")
    op.drop_table("refresh_tokens")

    # Remove session_id from workflows
    op.drop_index(op.f("ix_workflows_session_id"), table_name="workflows")
    op.drop_column("workflows", "session_id")

    # Remove OAuth indexes
    op.drop_index(op.f("ix_users_google_id"), table_name="users")
    op.drop_index(op.f("ix_users_apple_id"), table_name="users")

    # Make hashed_password required again
    op.alter_column("users", "hashed_password", nullable=False)

    # Remove OAuth columns from users
    op.drop_column("users", "auth_provider")
    op.drop_column("users", "email_verified")
    op.drop_column("users", "avatar_url")
    op.drop_column("users", "google_id")
    op.drop_column("users", "apple_id")
