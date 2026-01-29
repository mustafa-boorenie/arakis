"""Add cost_mode to workflows

Revision ID: 2026_01_29_1531
Revises: 2026_01_20_add_workflow_stages_tables
Create Date: 2026-01-29 15:31:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2026_01_29_1531'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add cost_mode column to workflows table."""
    # Add cost_mode column with default 'BALANCED'
    op.add_column(
        'workflows',
        sa.Column('cost_mode', sa.String(20), nullable=False, server_default='BALANCED')
    )
    
    # Remove server_default after setting default for existing rows
    # (allows future inserts to specify their own value or use default)
    op.alter_column('workflows', 'cost_mode', server_default=None)


def downgrade() -> None:
    """Remove cost_mode column from workflows table."""
    op.drop_column('workflows', 'cost_mode')
