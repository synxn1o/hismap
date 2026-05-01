"""Add credibility and annotations columns to journal_entries.

Revision ID: 002
Revises: 001
Create Date: 2026-05-01
"""
from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("journal_entries", sa.Column("credibility", sa.JSON(), nullable=True))
    op.add_column("journal_entries", sa.Column("annotations", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("journal_entries", "annotations")
    op.drop_column("journal_entries", "credibility")
