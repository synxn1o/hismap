"""change era_context from VARCHAR(200) to TEXT

Revision ID: 005
Revises: 004
Create Date: 2026-05-03
"""
from alembic import op
import sqlalchemy as sa

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "journal_entries",
        "era_context",
        existing_type=sa.String(200),
        type_=sa.Text(),
    )


def downgrade() -> None:
    op.alter_column(
        "journal_entries",
        "era_context",
        existing_type=sa.Text(),
        type_=sa.String(200),
    )
