"""
Unit tests for scanner.py module.
"""

from datetime import datetime, timezone
from pathlib import Path
import tempfile
import time
import pytest

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
    books_dir, podcasts_dir, cache_dir, cache_db = temp_library

    scanner = LibraryScanner(
        books_dir=books_dir, podcasts_dir=podcasts_dir, db_path=cache_db
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

    # Query SQLite cache directly
    cached_shows = scanner.cache.get_all_shows()
    assert len(cached_shows) == 2

    # Query cached show with episodes
    show_id = book_show_data["show_id"]
    cached_show = scanner.cache.get_show(show_id)
    assert cached_show is not None
    assert len(cached_show["episodes"]) == 3
    assert cached_show["episodes"][0]["filename"] == "01_chapter1.wav"


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


def test_clean_track_title() -> None:
    """Test clean_track_title automatically cleans x-delimited track titles while preserving standard titles."""
    from lissn.scanner import clean_track_title

    # User provided examples
    assert clean_track_title("01xMennxsomxhaterxkvinner") == "01 Menn som hater kvinner"
    assert clean_track_title("02xBokinformasjon") == "02 Bokinformasjon"
    assert clean_track_title("03xBokomtalexogxforfatteromtale") == "03 Bokomtale og forfatteromtale"
    assert clean_track_title("04xPROLOGxxFredagx1xxnovember") == "04 PROLOG Fredag 1 november"
    assert clean_track_title("05xDELx1xxINCITAMENTxx20xxdesemberxtilx3xxjanuar") == "05 DEL 1 INCITAMENT 20 desember til 3 januar"
    assert clean_track_title("06xKapittelx1xFredagx20xxdesember") == "06 Kapittel 1 Fredag 20 desember"
    assert clean_track_title("07xKapittelx2xxFredagx20xxdesember") == "07 Kapittel 2 Fredag 20 desember"
    assert (
        clean_track_title("08xKapittelx3xxFredagx20xxdesemberxxxlxrdagx21xxdesember")
        == "08 Kapittel 3 Fredag 20 desember lxrdag 21 desember"
    )
    assert (
        clean_track_title("09xKapittelx4xxMandagx23xxdesemberxxxtorsdagx26xxdesember")
        == "09 Kapittel 4 Mandag 23 desember torsdag 26 desember"
    )

    # Standard titles should remain unchanged
    assert clean_track_title("01 - Prologue") == "01 - Prologue"
    assert clean_track_title("Track 01") == "Track 01"
    assert clean_track_title("Index") == "Index"
    assert clean_track_title("Taxi Driver") == "Taxi Driver"
    assert clean_track_title("") == ""


def test_get_audio_title_and_norwegian_characters(tmp_path: Path) -> None:
    """Test get_audio_title preserves Norwegian characters in titles and filenames and cleans x-delimited titles."""
    from lissn.scanner import get_audio_title

    # Test filename stem fallback with Norwegian characters
    audio_file = tmp_path / "Blodsbrødre.mp3"
    audio_file.write_bytes(b"dummy mp3 data")

    title = get_audio_title(audio_file)
    assert title == "Blodsbrødre"

    # Test x-delimited track title
    x_file = tmp_path / "01xMennxsomxhaterxkvinner.mp3"
    x_file.write_bytes(b"dummy mp3 data")

    title_x = get_audio_title(x_file)
    assert title_x == "01 Menn som hater kvinner"


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


def test_multi_disc_folder_sorting_and_titles(tmp_path: Path) -> None:
    """Test multi-disc folder scanning sorts discs naturally and prefixes subfolder names to track titles."""
    books_dir = tmp_path / "books"
    podcasts_dir = tmp_path / "podcasts"
    cache_dir = tmp_path / "cache"
    db_path = cache_dir / "lissn.db"

    show_folder = books_dir / "Syden"
    disc1 = show_folder / "Syden Disc 1"
    disc2 = show_folder / "Syden Disc 2"
    disc1.mkdir(parents=True)
    disc2.mkdir(parents=True)

    (disc2 / "01 1.mp3").write_bytes(b"disc 2 track 1")
    (disc2 / "02 2.mp3").write_bytes(b"disc 2 track 2")
    (disc1 / "01 Spor 1.mp3").write_bytes(b"disc 1 track 1")
    (disc1 / "02 Spor 2.mp3").write_bytes(b"disc 1 track 2")

    scanner = LibraryScanner(
        books_dir=books_dir, podcasts_dir=podcasts_dir, cache_dir=cache_dir, db_path=db_path
    )
    scanner.scan_all()

    shows = scanner.cache.get_all_shows()
    show = scanner.cache.get_show(shows[0]["show_id"])
    assert show is not None
    episodes = show["episodes"]

    assert len(episodes) == 4
    assert episodes[0]["filename"] == "Syden Disc 1/01 Spor 1.mp3"
    assert episodes[0]["title"] == "Syden Disc 1 - 01 Spor 1"
    assert episodes[1]["filename"] == "Syden Disc 1/02 Spor 2.mp3"
    assert episodes[1]["title"] == "Syden Disc 1 - 02 Spor 2"
    assert episodes[2]["filename"] == "Syden Disc 2/01 1.mp3"
    assert episodes[2]["title"] == "Syden Disc 2 - 01 1"
    assert episodes[3]["filename"] == "Syden Disc 2/02 2.mp3"
    assert episodes[3]["title"] == "Syden Disc 2 - 02 2"


def test_update_show_metadata_and_cover_non_existent(tmp_path: Path) -> None:
    """Test scanner update_show_metadata and update_show_cover return None for invalid show IDs."""
    from lissn.scanner import LibraryScanner

    books_dir = tmp_path / "books"
    podcasts_dir = tmp_path / "podcasts"
    cache_dir = tmp_path / "cache"
    db_path = cache_dir / "lissn.db"
    books_dir.mkdir()
    podcasts_dir.mkdir()

    scanner = LibraryScanner(
        books_dir=books_dir, podcasts_dir=podcasts_dir, cache_dir=cache_dir, db_path=db_path
    )

    # Call with non-existent show ID
    res_meta = scanner.update_show_metadata("invalid_id", "Title", "Author", "Desc")
    assert res_meta is None

    res_cover = scanner.update_show_cover("invalid_id", tmp_path / "cover.jpg")
    assert res_cover is None


def test_incremental_scanning_and_pruning(temp_library, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that incremental scan reuses cached metadata for unchanged files and prunes deleted shows."""
    books_dir, podcasts_dir, cache_dir, cache_db = temp_library

    scanner = LibraryScanner(
        books_dir=books_dir, podcasts_dir=podcasts_dir, cache_dir=cache_dir, db_path=cache_db
    )

    # Initial scan
    scanner.scan_all()

    call_count = 0

    def mock_get_audio_duration(file_path):
        nonlocal call_count
        call_count += 1
        return 42.0

    monkeypatch.setattr("lissn.scanner.get_audio_duration", mock_get_audio_duration)

    # Second scan (incremental, force=False): no files modified
    call_count = 0
    res_incremental = scanner.scan_all(force=False)
    assert res_incremental["total"] == 2
    assert call_count == 0  # mutagen metadata extraction bypassed for all unchanged files!

    # Modify one audio file
    target_book_file = books_dir / "The Great Gatsby" / "01_chapter1.wav"
    time.sleep(0.01)
    target_book_file.write_bytes(b"modified audio data stream")

    # Third scan: only the modified file should trigger get_audio_duration
    call_count = 0
    scanner.scan_all(force=False)
    assert call_count == 1

    # Force scan: all files re-parsed regardless of mtime
    call_count = 0
    scanner.scan_all(force=True)
    assert call_count == 4  # 3 chapters in book + 1 in podcast

    # Pruning test: remove podcast show directory
    podcast_show_dir = podcasts_dir / "Tech Talk Podcast"
    import shutil
    shutil.rmtree(podcast_show_dir)

    res_pruned = scanner.scan_all()
    assert res_pruned["total"] == 1
    shows_in_db = scanner.cache.get_all_shows()
    assert len(shows_in_db) == 1
    assert shows_in_db[0]["section"] == "books"


def test_scanner_handles_empty_directories(tmp_path: Path) -> None:
    """Test LibraryScanner scanning completely empty library folders without errors."""
    books_dir = tmp_path / "empty_books"
    podcasts_dir = tmp_path / "empty_podcasts"
    cache_db = tmp_path / "test.db"

    books_dir.mkdir()
    podcasts_dir.mkdir()

    scanner = LibraryScanner(
        books_dir=books_dir, podcasts_dir=podcasts_dir, db_path=cache_db
    )
    result = scanner.scan_all()

    assert result["total"] == 0
    assert result["books"] == []
    assert result["podcasts"] == []


def test_publisher_metadata_parsing_and_update(tmp_path: Path) -> None:
    """Test metadata updating for publisher field in podcasts."""
    from lissn.scanner import ScannerCache, LibraryScanner

    db_path = tmp_path / "cache.db"
    cache = ScannerCache(db_path)
    
    show_id = "test_show_1"
    show_data = {
        "show_id": show_id,
        "section": "podcasts",
        "title": "Test Podcast",
        "author": "",
        "publisher": "Penguin Random House",
        "podcast_name": "Test Podcast",
        "folder_path": str(tmp_path),
        "cover_path": "",
        "total_duration": 100.0,
        "formatted_duration": "1m 40s",
        "total_file_size": 1024,
        "formatted_total_file_size": "1.0 KB",
        "added_timestamp": 123456789.0,
        "fuzzy_added_date": "Recently",
        "description": "Podcast description.",
        "description_html": "<p>Podcast description.</p>",
        "notes_path": "",
    }

    cache.save_show(show_data, [])
    fetched = cache.get_show(show_id)
    assert fetched is not None
    assert fetched["publisher"] == "Penguin Random House"

    scanner = LibraryScanner(books_dir=tmp_path, podcasts_dir=tmp_path, db_path=db_path)
    scanner.cache = cache

    updated = scanner.update_show_metadata(
        show_id=show_id,
        title="Updated Title",
        description="New description",
        publisher="HarperCollins"
    )
    assert updated is not None
    assert updated["publisher"] == "HarperCollins"
    assert updated["author"] == ""


def test_custom_cover_persists_across_scanner_restart(temp_library) -> None:
    """Test that setting a custom show cover persists in SQLite database and is retained after a scanner restart."""
    books_dir, podcasts_dir, cache_dir, cache_db = temp_library

    show_folder = books_dir / "The Great Gatsby"
    default_cover = show_folder / "cover.jpg"
    default_cover.write_bytes(b"default cover jpg content")

    custom_cover = show_folder / "alternate_cover.png"
    custom_cover.write_bytes(b"custom cover png content")

    scanner1 = LibraryScanner(
        books_dir=books_dir, podcasts_dir=podcasts_dir, db_path=cache_db
    )
    res1 = scanner1.scan_all()
    show_id = res1["books"][0]["show_id"]

    # Select custom cover
    updated = scanner1.update_show_cover(show_id, custom_cover)
    assert updated is not None
    assert updated["cover_path"] == str(custom_cover.resolve())

    # Simulate app restart with a fresh LibraryScanner instance
    scanner2 = LibraryScanner(
        books_dir=books_dir, podcasts_dir=podcasts_dir, db_path=cache_db
    )
    res2 = scanner2.scan_all()

    restarted_show = scanner2.cache.get_show(show_id)
    assert restarted_show is not None
    assert restarted_show["cover_path"] == str(custom_cover.resolve())


def test_sqlite_blob_cover_storage(temp_library) -> None:
    """Test storing cover binary BLOBs in SQLite and retrieving bytes via get_show_cover_data."""
    books_dir, podcasts_dir, cache_dir, cache_db = temp_library

    scanner = LibraryScanner(
        books_dir=books_dir, podcasts_dir=podcasts_dir, db_path=cache_db
    )
    res = scanner.scan_all()
    show_id = res["books"][0]["show_id"]

    raw_blob_bytes = b"\x89PNG\r\n\x1a\nfake_sqlite_png_blob_bytes"
    updated = scanner.update_show_cover_data(show_id, raw_blob_bytes, "image/png", "custom_cover.png")
    assert updated is not None

    blob_data = scanner.cache.get_show_cover_data(show_id)
    assert blob_data is not None
    bytes_out, mime_out = blob_data
    assert bytes_out == raw_blob_bytes
    assert mime_out == "image/png"

    # Verify scan_all retains SQLite BLOB across rescans
    scanner.scan_all()
    retained_blob = scanner.cache.get_show_cover_data(show_id)
    assert retained_blob is not None
    assert retained_blob[0] == raw_blob_bytes


def test_episode_sort_key_folder_first_and_natural_sorting() -> None:
    """Test episode_sort_key orders files folder-first and naturally by filename."""
    from lissn.scanner import episode_sort_key

    raw_files = [
        "CD 10/01 Track.mp3",
        "CD 2/01 Track.mp3",
        "CD 1/10 Track.mp3",
        "CD 1/02 Track.mp3",
        "CD 1/01 Track.mp3",
        "00 Intro.mp3",
    ]

    sorted_files = sorted(raw_files, key=episode_sort_key)

    expected = [
        "00 Intro.mp3",
        "CD 1/01 Track.mp3",
        "CD 1/02 Track.mp3",
        "CD 1/10 Track.mp3",
        "CD 2/01 Track.mp3",
        "CD 10/01 Track.mp3",
    ]

    assert sorted_files == expected


def test_library_scanner_sorts_episodes_folder_first_naturally(tmp_path: Path) -> None:
    """Test LibraryScanner scans and caches episodes sorted by folder first, then naturally by filename."""
    books_dir = tmp_path / "books"
    podcasts_dir = tmp_path / "podcasts"
    cache_dir = tmp_path / "cache"
    db_path = cache_dir / "test.db"

    books_dir.mkdir()
    podcasts_dir.mkdir()
    cache_dir.mkdir()

    book_dir = books_dir / "Complex Audiobook"
    book_dir.mkdir()

    (book_dir / "CD 10").mkdir()
    (book_dir / "CD 2").mkdir()
    (book_dir / "CD 1").mkdir()

    (book_dir / "CD 10" / "01.wav").write_bytes(b"data")
    (book_dir / "CD 2" / "01.wav").write_bytes(b"data")
    (book_dir / "CD 1" / "10.wav").write_bytes(b"data")
    (book_dir / "CD 1" / "02.wav").write_bytes(b"data")
    (book_dir / "CD 1" / "01.wav").write_bytes(b"data")
    (book_dir / "00_Intro.wav").write_bytes(b"data")

    scanner = LibraryScanner(
        books_dir=books_dir, podcasts_dir=podcasts_dir, cache_dir=cache_dir, db_path=db_path
    )
    res = scanner.scan_all()
    assert res["total"] == 1

    show = scanner.cache.get_show(res["books"][0]["show_id"])
    assert show is not None

    filenames = [ep["filename"] for ep in show["episodes"]]
    expected_filenames = [
        "00_Intro.wav",
        "CD 1/01.wav",
        "CD 1/02.wav",
        "CD 1/10.wav",
        "CD 2/01.wav",
        "CD 10/01.wav",
    ]
    assert filenames == expected_filenames








