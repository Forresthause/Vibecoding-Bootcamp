"""SQLite persistence for the research tracker.

Call init_db() at app startup, then use add_item() and get_items().
All functions accept an optional database path for testing.
"""

import sqlite3
from contextlib import closing
from pathlib import Path


DB_PATH = Path(__file__).resolve().parent / "research.db"


def init_db(db_path=DB_PATH):
    """Create the items table if it does not already exist."""
    with closing(sqlite3.connect(db_path)) as connection:
        with connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS research_items (
                    id INTEGER PRIMARY KEY,
                    title TEXT NOT NULL CHECK (length(trim(title)) > 0),
                    source TEXT NOT NULL DEFAULT '',
                    notes TEXT NOT NULL DEFAULT '',
                    tags TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )


def add_item(title, source="", notes="", tags="", db_path=DB_PATH):
    """Save an item and return its ID. Tags are comma-separated text."""
    title = title.strip()
    if not title:
        raise ValueError("Title must not be empty.")

    tags = ", ".join(tag.strip().lower() for tag in tags.split(",") if tag.strip())
    with closing(sqlite3.connect(db_path)) as connection:
        with connection:
            cursor = connection.execute(
                """
                INSERT INTO research_items (title, source, notes, tags)
                VALUES (?, ?, ?, ?)
                """,
                (title, source.strip(), notes.strip(), tags),
            )
            return cursor.lastrowid


def get_items(search="", db_path=DB_PATH):
    """Return item dictionaries, newest first, optionally matching literal text.

    Search checks title, source, notes, and tags for a substring. SQLite's
    default LIKE matching is case-insensitive for ASCII characters.
    """
    query = "SELECT id, title, source, notes, tags, created_at FROM research_items"
    parameters = ()
    search = search.strip()
    if search:
        # Escape LIKE wildcards so user-entered % and _ match literally.
        search = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{search}%"
        query += """
            WHERE title LIKE ? ESCAPE '\\'
               OR source LIKE ? ESCAPE '\\'
               OR notes LIKE ? ESCAPE '\\'
               OR tags LIKE ? ESCAPE '\\'
        """
        parameters = (pattern,) * 4
    query += " ORDER BY created_at DESC, id DESC"

    with closing(sqlite3.connect(db_path)) as connection:
        connection.row_factory = sqlite3.Row
        return [dict(row) for row in connection.execute(query, parameters)]
