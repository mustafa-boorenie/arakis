"""Add workflow stage checkpoints, figures, and tables.

Adds support for 12-stage workflow with checkpointing, R2 figure storage,
and generated tables (study characteristics, RoB, GRADE).

Revision ID: a1b2c3d4e5f6
Revises: f0a7b8c9d1e4
Create Date: 2026-01-20

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "f0a7b8c9d1e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Create workflow_stage_checkpoints table
    op.create_table(
        "workflow_stage_checkpoints",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "workflow_id",
            sa.String(36),
            sa.ForeignKey("workflows.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("stage", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), default="pending", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retry_count", sa.Integer(), default=0, nullable=False),
        sa.Column("output_data", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("cost", sa.Float(), default=0.0, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=True,
        ),
        sa.UniqueConstraint("workflow_id", "stage", name="uq_workflow_stage"),
    )
    op.create_index(
        "ix_workflow_stage_checkpoints_workflow_id",
        "workflow_stage_checkpoints",
        ["workflow_id"],
    )
    op.create_index(
        "ix_workflow_stage_checkpoints_status",
        "workflow_stage_checkpoints",
        ["status"],
    )

    # 2. Create workflow_figures table
    op.create_table(
        "workflow_figures",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "workflow_id",
            sa.String(36),
            sa.ForeignKey("workflows.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("figure_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("caption", sa.Text(), nullable=True),
        sa.Column("r2_key", sa.String(500), nullable=True),
        sa.Column("r2_url", sa.String(1000), nullable=True),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_workflow_figures_workflow_id",
        "workflow_figures",
        ["workflow_id"],
    )

    # 3. Create workflow_tables table
    op.create_table(
        "workflow_tables",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "workflow_id",
            sa.String(36),
            sa.ForeignKey("workflows.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("table_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("caption", sa.Text(), nullable=True),
        sa.Column("headers", sa.JSON(), nullable=True),
        sa.Column("rows", sa.JSON(), nullable=True),
        sa.Column("footnotes", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_workflow_tables_workflow_id",
        "workflow_tables",
        ["workflow_id"],
    )

    # 4. Add new columns to workflows table
    op.add_column(
        "workflows",
        sa.Column("needs_user_action", sa.Boolean(), default=False, nullable=True),
    )
    op.add_column(
        "workflows",
        sa.Column("action_required", sa.Text(), nullable=True),
    )
    op.add_column(
        "workflows",
        sa.Column("meta_analysis_feasible", sa.Boolean(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove columns from workflows
    op.drop_column("workflows", "meta_analysis_feasible")
    op.drop_column("workflows", "action_required")
    op.drop_column("workflows", "needs_user_action")

    # Drop tables
    op.drop_index("ix_workflow_tables_workflow_id", table_name="workflow_tables")
    op.drop_table("workflow_tables")

    op.drop_index("ix_workflow_figures_workflow_id", table_name="workflow_figures")
    op.drop_table("workflow_figures")

    op.drop_index("ix_workflow_stage_checkpoints_status", table_name="workflow_stage_checkpoints")
    op.drop_index(
        "ix_workflow_stage_checkpoints_workflow_id",
        table_name="workflow_stage_checkpoints",
    )
    op.drop_table("workflow_stage_checkpoints")
