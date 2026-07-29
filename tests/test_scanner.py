"""
Unit tests for scanner.py module.
"""

from datetime import datetime, timezone
from pathlib import Path
import tempfile
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
    """Test full directory scanning, notes.md auto-generation, and SQLite cache operations."""
    books_dir, podcasts_dir, cache_dir, cache_db = temp_library

    scanner = LibraryScanner(
        books_dir=books_dir, podcasts_dir=podcasts_dir, cache_dir=cache_dir, db_path=cache_db
    )
    result = scanner.scan_all()

    assert result["total"] == 2
    assert len(result["books"]) == 1
    assert len(result["podcasts"]) == 1

    # Verify books show details
    book_show_data = result["books"][0]
    assert book_show_data["title"] == "The Great Gatsby"
    assert book_show_data["section"] == "books"
    assert book_show_data["total_duration"] == 18.0
    assert book_show_data["cover_path"] is not None

    # Verify auto-created notes.md file in cache_dir
    notes_file = cache_dir / "books" / "The Great Gatsby" / "notes.md"
    assert notes_file.exists()
    assert "Unknown Author" in notes_file.read_text()

    # Query SQLite cache directly
    cached_shows = scanner.cache.get_all_shows()
    assert len(cached_shows) == 2

    # Query cached show with episodes
    show_id = book_show_data["show_id"]
    cached_show = scanner.cache.get_show(show_id)
    assert cached_show is not None
    assert len(cached_show["episodes"]) == 3
    assert cached_show["episodes"][0]["filename"] == "01_chapter1.wav"


def test_notes_md_customization(temp_library) -> None:
    """Test custom metadata and markdown rendering parsed from notes.md in cache_dir."""
    books_dir, podcasts_dir, cache_dir, cache_db = temp_library

    notes_file = cache_dir / "books" / "The Great Gatsby" / "notes.md"
    notes_file.parent.mkdir(parents=True, exist_ok=True)
    notes_file.write_text(
        """---
title: "The Great Gatsby (Annotated)"
author: "F. Scott Fitzgerald"
---

# About this Audiobook

This is a **classic** American novel.
""",
        encoding="utf-8",
    )

    scanner = LibraryScanner(
        books_dir=books_dir, podcasts_dir=podcasts_dir, cache_dir=cache_dir, db_path=cache_db
    )
    result = scanner.scan_all()

    book = result["books"][0]
    assert book["title"] == "The Great Gatsby (Annotated)"
    assert book["author"] == "F. Scott Fitzgerald"
    assert "<strong>classic</strong>" in book["description_html"]


def test_scanner_handles_empty_directories(tmp_path: Path) -> None:
    """Test LibraryScanner scanning completely empty library folders without errors."""
    books_dir = tmp_path / "empty_books"
    podcasts_dir = tmp_path / "empty_podcasts"
    cache_dir = tmp_path / "cache"
    cache_db = cache_dir / "test.db"

    books_dir.mkdir()
    podcasts_dir.mkdir()
    cache_dir.mkdir()

    scanner = LibraryScanner(
        books_dir=books_dir, podcasts_dir=podcasts_dir, cache_dir=cache_dir, db_path=cache_db
    )
    result = scanner.scan_all()

    assert result["total"] == 0
    assert len(result["books"]) == 0
    assert len(result["podcasts"]) == 0


def test_scanner_skips_non_audio_files(temp_library) -> None:
    """Test LibraryScanner ignores non-audio files (like text files, images, or metadata)."""
    books_dir, podcasts_dir, cache_dir, cache_db = temp_library

    book_show = books_dir / "The Great Gatsby"
    (book_show / "notes_local.txt").write_text("Some text info")
    (book_show / ".DS_Store").write_bytes(b"\x00\x00")

    scanner = LibraryScanner(
        books_dir=books_dir, podcasts_dir=podcasts_dir, cache_dir=cache_dir, db_path=cache_db
    )
    result = scanner.scan_all()

    book_summary = result["books"][0]
    show_detail = scanner.cache.get_show(book_summary["show_id"])
    filenames = [ep["filename"] for ep in show_detail["episodes"]]

    assert "notes_local.txt" not in filenames
    assert ".DS_Store" not in filenames
    assert "01_chapter1.wav" in filenames


def test_format_file_size() -> None:
    """Test format_file_size converts bytes to human-readable strings."""
    from lissn.scanner import format_file_size

    assert format_file_size(0) == "0 B"
    assert format_file_size(500) == "500 B"
    assert format_file_size(1500) == "1.5 KB"
    assert format_file_size(15 * 1024 * 1024) == "15.00 MB"
    assert format_file_size(2 * 1024 * 1024 * 1024) == "2.00 GB"


def test_bitrate_formatting_and_calculation(tmp_path: Path) -> None:
    """Test get_audio_bitrate and format_bitrate utility functions."""
    from lissn.scanner import format_bitrate, get_audio_bitrate

    assert format_bitrate(0) == "N/A"
    assert format_bitrate(128) == "128 kbps"

    # Test calculated bitrate fallback for 10 seconds of 160KB file (160000 bytes * 8 / (10 * 1000) = 128 kbps)
    test_file = tmp_path / "test.mp3"
    test_file.write_bytes(b"0" * 160000)

    bitrate = get_audio_bitrate(test_file, file_size=160000, duration=10.0)
    assert bitrate == 128


def test_max_episodes_per_show_limit(tmp_path: Path) -> None:
    """Test max_episodes_per_show truncates episode list during scanning."""
    books_dir = tmp_path / "books"
    podcasts_dir = tmp_path / "podcasts"
    cache_dir = tmp_path / "cache"
    cache_db = cache_dir / "db.sqlite"

    show_dir = podcasts_dir / "Huge Podcast"
    show_dir.mkdir(parents=True, exist_ok=True)

    # Create 10 fake episode files
    for i in range(1, 11):
        (show_dir / f"episode_{i:02d}.mp3").write_bytes(b"dummy content")

    # Scanner with max_episodes_per_show = 3
    scanner = LibraryScanner(
        books_dir=books_dir,
        podcasts_dir=podcasts_dir,
        cache_dir=cache_dir,
        db_path=cache_db,
        max_episodes_per_show=3,
    )
    result = scanner.scan_all()

    show = result["podcasts"][0]
    show_detail = scanner.cache.get_show(show["show_id"])
    assert len(show_detail["episodes"]) == 3
    assert show_detail["episodes"][0]["filename"] == "episode_01.mp3"
    assert show_detail["episodes"][2]["filename"] == "episode_03.mp3"


def test_decode_metadata_text() -> None:
    """Test decode_metadata_text extracts strings and fixes double-encoded UTF-8 strings."""
    from lissn.scanner import decode_metadata_text

    assert decode_metadata_text(None) == ""
    assert decode_metadata_text(["Blodsbrødre"]) == "Blodsbrødre"
    assert decode_metadata_text("Blodsbrødre") == "Blodsbrødre"

    # Test double-encoded UTF-8 string ('Blodsbr\xc3\xb8dre' read as Latin-1)
    double_encoded = "Blodsbrødre".encode("utf-8").decode("latin-1")
    assert decode_metadata_text(double_encoded) == "Blodsbrødre"


def test_get_audio_title_and_norwegian_characters(tmp_path: Path) -> None:
    """Test get_audio_title preserves Norwegian characters in titles and filenames."""
    from lissn.scanner import get_audio_title

    # Test filename stem fallback with Norwegian characters
    audio_file = tmp_path / "Blodsbrødre.mp3"
    audio_file.write_bytes(b"dummy mp3 data")

    title = get_audio_title(audio_file)
    assert title == "Blodsbrødre"


def test_identical_track_titles_renamed_to_track_n(tmp_path: Path) -> None:
    """Test scanner renames track titles to 'Track 1', 'Track 2', etc. when all tracks in a show have identical metadata titles."""
    from lissn.scanner import LibraryScanner

    books_dir = tmp_path / "books"
    podcasts_dir = tmp_path / "podcasts"
    cache_dir = tmp_path / "cache"
    db_path = cache_dir / "lissn.db"

    show_folder = books_dir / "Identical Tracks Book"
    show_folder.mkdir(parents=True)

    # Create multiple audio files with identical names (or fallback stem if identical)
    (show_folder / "SameName.mp3").write_bytes(b"dummy mp3 data 1")
    (show_folder / "SameName.m4a").write_bytes(b"dummy mp3 data 2")

    scanner = LibraryScanner(
        books_dir=books_dir, podcasts_dir=podcasts_dir, cache_dir=cache_dir, db_path=db_path
    )

    scanned = scanner.scan_all()
    assert scanned["total"] == 1

    shows = scanner.cache.get_all_shows()
    assert len(shows) == 1
    show_id = shows[0]["show_id"]

    show = scanner.cache.get_show(show_id)
    assert show is not None
    episodes = show["episodes"]
    assert len(episodes) == 2
    assert episodes[0]["title"] == "Track 1"
    assert episodes[1]["title"] == "Track 2"


def test_subfolder_scanning(tmp_path: Path) -> None:
    """Test scanner indexes audio files located inside nested subfolders with relative filenames."""
    books_dir = tmp_path / "books"
    podcasts_dir = tmp_path / "podcasts"
    cache_dir = tmp_path / "cache"
    db_path = cache_dir / "lissn.db"

    show_folder = podcasts_dir / "Papaya"
    sub_folder = show_folder / "Papaya.2026.1901-2101"
    sub_folder.mkdir(parents=True)

    # Create files matching user report scenario
    (sub_folder / "Papaya.2026-01-19.mp3").write_bytes(b"dummy audio data 1")
    (sub_folder / "Papaya.2026-01-20.mp3").write_bytes(b"dummy audio data 2")

    scanner = LibraryScanner(
        books_dir=books_dir, podcasts_dir=podcasts_dir, cache_dir=cache_dir, db_path=db_path
    )

    scanned = scanner.scan_all()
    assert scanned["total"] == 1

    show = scanner.cache.get_show(scanned["podcasts"][0]["show_id"])
    assert show is not None
    episodes = show["episodes"]
    assert len(episodes) == 2
    assert episodes[0]["filename"] == "Papaya.2026.1901-2101/Papaya.2026-01-19.mp3"
    assert episodes[1]["filename"] == "Papaya.2026.1901-2101/Papaya.2026-01-20.mp3"


