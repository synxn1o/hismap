"""Add importance column to entry_locations.

Revision ID: 003
Revises: 002
Create Date: 2026-05-02
"""
from alembic import op
import sqlalchemy as sa

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "entry_locations",
        sa.Column("importance", sa.Integer(), server_default="0", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("entry_locations", "importance")
