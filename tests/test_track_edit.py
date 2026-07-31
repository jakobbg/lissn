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


