"""Add progress_data to workflow_stage_checkpoints

Revision ID: 2026_01_29_1700
Revises: 2026_01_29_1531
Create Date: 2026-01-29 17:00:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2026_01_29_1700"
down_revision: Union[str, None] = "2026_01_29_1531"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add progress_data column to workflow_stage_checkpoints table."""
    op.add_column(
        "workflow_stage_checkpoints",
        sa.Column("progress_data", sa.JSON, nullable=True),
    )


def downgrade() -> None:
    """Remove progress_data column from workflow_stage_checkpoints table."""
    op.drop_column("workflow_stage_checkpoints", "progress_data")
