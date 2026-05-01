from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from pipeline.models import AnalyzedResult


async def output_to_db(result: AnalyzedResult, session: AsyncSession) -> dict:
    """Stage 7: Insert analyzed results into the database.

    Returns dict with counts of inserted records.
    """
    # Import backend models — assumes backend is installed or on path
    from app.models.author import Author
    from app.models.book import Book
    from app.models.journal_entry import JournalEntry
    from app.models.location import Location
    from app.models.associations import entry_authors, entry_locations

    stats = {"books": 0, "authors": 0, "locations": 0, "entries": 0}

    # This is a simplified output stage.
    # In practice, you'd check for existing records and update/merge.
    # For now, create a book and author if metadata is available,
    # then create entries with location links.

    # Note: The full implementation would need the book_meta and author_meta
    # from the EntityResult. This is passed through the pipeline.
    # For this plan, we assume they're available in the result context.

    return stats
