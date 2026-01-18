"""Add phone_number to users table.

Revision ID: f0a7b8c9d1e4
Revises: e9b6f7c8d0f3
Create Date: 2026-01-17

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f0a7b8c9d1e4'
down_revision = 'e9b6f7c8d0f3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add phone_number column to users table
    op.add_column('users', sa.Column('phone_number', sa.String(20), nullable=True))


def downgrade() -> None:
    # Remove phone_number column from users table
    op.drop_column('users', 'phone_number')
