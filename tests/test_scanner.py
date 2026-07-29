"""
Unit tests for scanner.py module.
"""

from datetime import datetime, timezone
from pathlib import Path
import time

from lissn.scanner import (
    LibraryScanner,
    ScannerCache,
    format_duration,
    format_fuzzy_date,
    generate_show_id,
)


def test_generate_show_id() -> None:
    """Test show ID generation produces consistent sha256 prefix hashes."""
    id1 = generate_show_id("books", "Dune")
    id2 = generate_show_id("books", "Dune")
    id3 = generate_show_id("podcasts", "Dune")

    assert id1 == id2
    assert id1 != id3
    assert len(id1) == 16


def test_format_duration() -> None:
    """Test formatting seconds into readable duration strings."""
    assert format_duration(0) == "0m"
    assert format_duration(45) == "45s"
    assert format_duration(125) == "2m 5s"
    assert format_duration(3660) == "1h 1m"
    assert format_duration(7200) == "2h"


def test_format_fuzzy_date() -> None:
    """Test formatting timestamps into relative fuzzy dates."""
    now = datetime.now(timezone.utc).timestamp()
    assert format_fuzzy_date(now - 10) == "Just now"
    assert format_fuzzy_date(now - 3600 * 2) == "Today"
    assert format_fuzzy_date(now - 86400 * 1) == "Yesterday"
    assert format_fuzzy_date(now - 86400 * 3) == "3 days ago"
    assert format_fuzzy_date(now - 86400 * 14) == "2 weeks ago"
    assert format_fuzzy_date(now - 86400 * 60) == "2 months ago"
    assert format_fuzzy_date(now - 86400 * 400) == "1 year ago"


def test_library_scanner_and_cache(temp_library) -> None:
    """Test full directory scanning and SQLite cache operations."""
    books_dir, podcasts_dir, cache_db = temp_library

    scanner = LibraryScanner(books_dir=books_dir, podcasts_dir=podcasts_dir, db_path=cache_db)
    result = scanner.scan_all()

    assert result["total"] == 2
    assert len(result["books"]) == 1
    assert len(result["podcasts"]) == 1

    # Verify books show details
    book_show_data = result["books"][0]
    assert book_show_data["title"] == "The Great Gatsby"
    assert book_show_data["section"] == "books"
    assert book_show_data["description"] == "A novel by F. Scott Fitzgerald."
    assert book_show_data["total_duration"] == 15.0
    assert book_show_data["cover_path"] is not None

    # Query SQLite cache directly
    cached_shows = scanner.cache.get_all_shows()
    assert len(cached_shows) == 2

    # Query cached show with episodes
    show_id = book_show_data["show_id"]
    cached_show = scanner.cache.get_show(show_id)
    assert cached_show is not None
    assert len(cached_show["episodes"]) == 2
    assert cached_show["episodes"][0]["filename"] == "01_chapter1.wav"
