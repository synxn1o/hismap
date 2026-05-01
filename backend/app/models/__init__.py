from app.models.associations import entry_authors, entry_locations, relation_locations
from app.models.author import Author
from app.models.book import Book
from app.models.journal_entry import JournalEntry
from app.models.location import Location

__all__ = [
    "Author",
    "Book",
    "JournalEntry",
    "Location",
    "entry_authors",
    "entry_locations",
    "relation_locations",
]
