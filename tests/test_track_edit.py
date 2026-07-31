"""Unit and integration tests for track title editing."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from lissn.app import app, scanner
from lissn.scanner import ScannerCache


def test_scanner_cache_update_episode_title(tmp_path: Path):
    """Test updating episode title directly in SQLite ScannerCache."""
    db_path = tmp_path / "test_cache.db"
    cache = ScannerCache(db_path)

    show_data = {
        "show_id": "test-show-1",
        "section": "books",
        "title": "Test Audiobook",
        "folder_path": str(tmp_path),
        "total_duration": 100.0,
        "formatted_duration": "01:40",
        "added_timestamp": 123456.0,
        "fuzzy_added_date": "Today",
    }
    episodes = [
        {
            "episode_id": "ep-1",
            "show_id": "test-show-1",
            "title": "Old Track Title",
            "filename": "track1.mp3",
            "file_path": str(tmp_path / "track1.mp3"),
            "duration": 100.0,
            "formatted_duration": "01:40",
            "file_size": 5000,
            "added_timestamp": 123456.0,
        }
    ]
    cache.save_show(show_data, episodes)

    # Test valid update
    updated_ep = cache.update_episode_title("test-show-1", "ep-1", "New Clean Track Title")
    assert updated_ep is not None
    assert updated_ep["title"] == "New Clean Track Title"

    # Verify retrieval from cache
    ep_map = cache.get_episodes_map("test-show-1")
    assert list(ep_map.values())[0]["title"] == "New Clean Track Title"

    # Test non-existent episode
    assert cache.update_episode_title("test-show-1", "ep-999", "Other") is None

    # Test empty title
    assert cache.update_episode_title("test-show-1", "ep-1", "   ") is None


def test_api_edit_episode_unauthenticated():
    """Test POST /api/shows/{show_id}/episodes/{episode_id}/edit without auth when password is required."""
    client = TestClient(app)
    from lissn.app import config

    with patch.object(config, "password", "testpass"):
        res = client.post(
            "/api/shows/show1/episodes/ep1/edit",
            json={"title": "New Title"},
        )
        assert res.status_code == 401


def test_api_edit_episode_success(tmp_path: Path):
    """Test POST /api/shows/{show_id}/episodes/{episode_id}/edit with auth."""
    client = TestClient(app)
    from lissn.app import config

    with patch.object(config, "password", ""):
        with patch.object(scanner, "update_episode_title") as mock_update:
            mock_update.return_value = {
                "episode_id": "ep-1",
                "show_id": "show-1",
                "title": "Renamed Track",
            }
            res = client.post(
                "/api/shows/show-1/episodes/ep-1/edit",
                json={"title": "Renamed Track"},
            )
            assert res.status_code == 200
            data = res.json()
            assert data["status"] == "success"
            assert data["episode"]["title"] == "Renamed Track"
            mock_update.assert_called_once_with(
                show_id="show-1", episode_id="ep-1", new_title="Renamed Track"
            )


def test_scanner_reset_show_track_titles(tmp_path: Path):
    """Test LibraryScanner.reset_show_track_titles resets titles to subfolder/tags or filename stem."""
    db_path = tmp_path / "test_cache.db"
    cache = ScannerCache(db_path)

    show_dir = tmp_path / "show1"
    sub_dir = show_dir / "Disc 1"
    sub_dir.mkdir(parents=True, exist_ok=True)
    audio_file1 = sub_dir / "01 - Intro.mp3"
    audio_file1.write_bytes(b"dummy mp3 data")

    audio_file2 = show_dir / "02 - Outro.mp3"
    audio_file2.write_bytes(b"dummy mp3 data")

    show_data = {
        "show_id": "show-1",
        "section": "books",
        "title": "Test Show",
        "folder_path": str(show_dir),
        "total_duration": 100.0,
        "formatted_duration": "01:40",
        "added_timestamp": 123456.0,
        "fuzzy_added_date": "Today",
    }
    episodes = [
        {
            "episode_id": "ep-1",
            "show_id": "show-1",
            "title": "Custom User Title 1",
            "filename": "Disc 1/01 - Intro.mp3",
            "file_path": str(audio_file1),
            "duration": 50.0,
            "formatted_duration": "00:50",
            "file_size": 5000,
            "added_timestamp": 123456.0,
        },
        {
            "episode_id": "ep-2",
            "show_id": "show-1",
            "title": "Custom User Title 2",
            "filename": "02 - Outro.mp3",
            "file_path": str(audio_file2),
            "duration": 50.0,
            "formatted_duration": "00:50",
            "file_size": 5000,
            "added_timestamp": 123456.0,
        },
    ]
    cache.save_show(show_data, episodes)

    from lissn.scanner import LibraryScanner

    scanner_inst = LibraryScanner(books_dir=tmp_path, podcasts_dir=tmp_path, db_path=db_path)
    scanner_inst.cache = cache

    updated_show = scanner_inst.reset_show_track_titles("show-1")
    assert updated_show is not None
    eps = {ep["episode_id"]: ep["title"] for ep in updated_show["episodes"]}

    # Track 1 has subfolder "Disc 1" -> "Disc 1/01 - Intro"
    assert eps["ep-1"] == "Disc 1/01 - Intro"
    # Track 2 has no subfolder -> "02 - Outro"
    assert eps["ep-2"] == "02 - Outro"


def test_api_reindex_tracks_unauthenticated():
    """Test POST /api/shows/{show_id}/reindex-tracks returns 401 when password required and unauthenticated."""
    client = TestClient(app)
    from lissn.app import config

    with patch.object(config, "password", "testpass"):
        res = client.post("/api/shows/show-1/reindex-tracks")
        assert res.status_code == 401


def test_api_reindex_tracks_success():
    """Test POST /api/shows/{show_id}/reindex-tracks with authentication."""
    client = TestClient(app)
    from lissn.app import config

    with patch.object(config, "password", ""):
        with patch.object(scanner, "reset_show_track_titles") as mock_reset:
            mock_reset.return_value = {
                "show_id": "show-1",
                "title": "Test Show",
                "episodes": [
                    {"episode_id": "ep-1", "title": "Disc 1/01 - Intro"},
                ],
            }
            res = client.post("/api/shows/show-1/reindex-tracks")
            assert res.status_code == 200
            data = res.json()
            assert data["status"] == "success"
            assert data["show"]["episodes"][0]["title"] == "Disc 1/01 - Intro"
            mock_reset.assert_called_once_with("show-1")


def test_scanner_reset_show_track_titles_duplicate_fallback(tmp_path: Path):
    """Test that when 2 tracks have duplicate tag titles, reset_show_track_titles falls back to filename stems."""
    db_path = tmp_path / "test_cache.db"
    cache = ScannerCache(db_path)

    show_dir = tmp_path / "show_dup"
    show_dir.mkdir(parents=True, exist_ok=True)
    audio1 = show_dir / "01_intro.mp3"
    audio2 = show_dir / "02_outro.mp3"
    audio1.write_bytes(b"dummy")
    audio2.write_bytes(b"dummy")

    show_data = {
        "show_id": "show-dup",
        "section": "books",
        "title": "Dup Show",
        "folder_path": str(show_dir),
        "total_duration": 100.0,
        "formatted_duration": "01:40",
        "added_timestamp": 123456.0,
        "fuzzy_added_date": "Today",
    }
    # Both episodes currently have the SAME title
    episodes = [
        {
            "episode_id": "ep-1",
            "show_id": "show-dup",
            "title": "Same Title",
            "filename": "01_intro.mp3",
            "file_path": str(audio1),
            "duration": 50.0,
            "formatted_duration": "00:50",
            "file_size": 5000,
            "added_timestamp": 123456.0,
        },
        {
            "episode_id": "ep-2",
            "show_id": "show-dup",
            "title": "Same Title",
            "filename": "02_outro.mp3",
            "file_path": str(audio2),
            "duration": 50.0,
            "formatted_duration": "00:50",
            "file_size": 5000,
            "added_timestamp": 123456.0,
        },
    ]
    cache.save_show(show_data, episodes)

    from lissn.scanner import LibraryScanner, get_audio_title

    with patch("lissn.scanner.get_audio_title", return_value="Same Title"):
        scanner_inst = LibraryScanner(books_dir=tmp_path, podcasts_dir=tmp_path, db_path=db_path)
        scanner_inst.cache = cache

        updated_show = scanner_inst.reset_show_track_titles("show-dup")
        assert updated_show is not None
        eps = {ep["episode_id"]: ep["title"] for ep in updated_show["episodes"]}

        # Both had tag title "Same Title" -> fallback to filename stems "01_intro" and "02_outro"
        assert eps["ep-1"] == "01_intro"
        assert eps["ep-2"] == "02_outro"


def test_update_episode_title_duplicate_error(tmp_path: Path):
    """Test that ScannerCache.update_episode_title raises ValueError on duplicate title in the same show."""
    db_path = tmp_path / "test_cache.db"
    cache = ScannerCache(db_path)

    show_data = {
        "show_id": "show-1",
        "section": "books",
        "title": "Test Show",
        "folder_path": str(tmp_path),
        "total_duration": 100.0,
        "formatted_duration": "01:40",
        "added_timestamp": 123456.0,
        "fuzzy_added_date": "Today",
    }
    episodes = [
        {
            "episode_id": "ep-1",
            "show_id": "show-1",
            "title": "Track One",
            "filename": "track1.mp3",
            "file_path": str(tmp_path / "track1.mp3"),
            "duration": 50.0,
            "formatted_duration": "00:50",
            "file_size": 5000,
            "added_timestamp": 123456.0,
        },
        {
            "episode_id": "ep-2",
            "show_id": "show-1",
            "title": "Track Two",
            "filename": "track2.mp3",
            "file_path": str(tmp_path / "track2.mp3"),
            "duration": 50.0,
            "formatted_duration": "00:50",
            "file_size": 5000,
            "added_timestamp": 123456.0,
        },
    ]
    cache.save_show(show_data, episodes)

    import pytest
    with pytest.raises(ValueError, match="already exists"):
        cache.update_episode_title("show-1", "ep-2", "Track One")


def test_api_edit_episode_duplicate_title():
    """Test POST /api/shows/{show_id}/episodes/{episode_id}/edit returns 400 when duplicate title is given."""
    client = TestClient(app)
    from lissn.app import config

    with patch.object(config, "password", ""):
        with patch.object(scanner, "update_episode_title", side_effect=ValueError("Track title 'Track One' already exists in this show")):
            res = client.post(
                "/api/shows/show-1/episodes/ep-2/edit",
                json={"title": "Track One"},
            )
            assert res.status_code == 400
            data = res.json()
            assert "already exists" in data["detail"]


def test_custom_track_title_persists_across_scans(tmp_path: Path):
    """Test that editing a track title sets is_custom_title and persists across LibraryScanner scans."""
    books_dir = tmp_path / "books"
    podcasts_dir = tmp_path / "podcasts"
    books_dir.mkdir()
    podcasts_dir.mkdir()

    book_dir = books_dir / "Neuromancer"
    book_dir.mkdir()
    audio_file = book_dir / "William Gibson - Neuromancer Part 1.mp3"
    audio_file.write_bytes(b"dummy audio content")

    db_path = tmp_path / "test_cache.db"
    from lissn.scanner import LibraryScanner

    scanner_inst = LibraryScanner(books_dir=books_dir, podcasts_dir=podcasts_dir, db_path=db_path)

    # 1. Initial scan
    scanner_inst.scan_all()
    shows = scanner_inst.cache.get_all_shows()
    assert len(shows) == 1
    show_id = shows[0]["show_id"]
    show = scanner_inst.cache.get_show(show_id)
    ep = show["episodes"][0]
    assert ep["title"] == "William Gibson - Neuromancer Part 1"
    assert ep.get("is_custom_title", 0) == 0

    # 2. Edit track title
    updated_ep = scanner_inst.update_episode_title(show_id, ep["episode_id"], "Neuromancer Part 1 (Custom)")
    assert updated_ep is not None
    assert updated_ep["title"] == "Neuromancer Part 1 (Custom)"
    assert updated_ep["is_custom_title"] == 1

    # 3. Simulate server restart / re-scan (scan_all)
    scanner_inst.scan_all()
    rescanned_show = scanner_inst.cache.get_show(show_id)
    rescanned_ep = rescanned_show["episodes"][0]
    assert rescanned_ep["title"] == "Neuromancer Part 1 (Custom)"
    assert rescanned_ep["is_custom_title"] == 1

    # 4. Re-index / reset track titles
    reset_show = scanner_inst.reset_show_track_titles(show_id)
    assert reset_show is not None
    reset_ep = reset_show["episodes"][0]
    assert reset_ep["title"] == "William Gibson - Neuromancer Part 1"
    assert reset_ep.get("is_custom_title", 0) == 0




