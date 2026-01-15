"""Add error_message to workflows

Revision ID: d8a5f6b7c9e2
Revises: cf5eebc3639a
Create Date: 2026-01-14 16:48:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d8a5f6b7c9e2"
down_revision: Union[str, Sequence[str], None] = "cf5eebc3639a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("workflows", sa.Column("error_message", sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("workflows", "error_message")
