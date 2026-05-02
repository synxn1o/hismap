"""pipeline revision — add excerpt/summary, remove old translations

Revision ID: 004
Revises: 003
Create Date: 2026-05-02
"""
from alembic import op
import sqlalchemy as sa

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns
    op.add_column("journal_entries", sa.Column("excerpt_original", sa.Text(), nullable=True))
    op.add_column("journal_entries", sa.Column("excerpt_translation", sa.Text(), nullable=True))
    op.add_column("journal_entries", sa.Column("summary_chinese", sa.Text(), nullable=True))
    op.add_column("journal_entries", sa.Column("summary_english", sa.Text(), nullable=True))
    op.add_column("journal_entries", sa.Column("persons", sa.JSON(), nullable=True))
    op.add_column("journal_entries", sa.Column("dates", sa.JSON(), nullable=True))

    # Remove old translation columns
    op.drop_column("journal_entries", "modern_translation")
    op.drop_column("journal_entries", "english_translation")


def downgrade() -> None:
    # Restore old columns
    op.add_column("journal_entries", sa.Column("modern_translation", sa.Text(), nullable=True))
    op.add_column("journal_entries", sa.Column("english_translation", sa.Text(), nullable=True))

    # Remove new columns
    op.drop_column("journal_entries", "dates")
    op.drop_column("journal_entries", "persons")
    op.drop_column("journal_entries", "summary_english")
    op.drop_column("journal_entries", "summary_chinese")
    op.drop_column("journal_entries", "excerpt_translation")
    op.drop_column("journal_entries", "excerpt_original")
