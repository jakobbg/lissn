"""
Unit tests for lissn.config module.
Verifies default configuration initializations, environment variable overrides,
JSON config file loading, and directory structure creation.
"""

import json
from pathlib import Path
import pytest

from lissn.config import Config


def test_config_defaults(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test Config default path initialization and fallback options when no env or file exists."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("LISSN_BOOKS_DIR", raising=False)
    monkeypatch.delenv("LISSN_PODCASTS_DIR", raising=False)
    monkeypatch.delenv("LISSN_CACHE_DIR", raising=False)
    monkeypatch.delenv("LISSN_CACHE_DB", raising=False)
    monkeypatch.delenv("LISSN_HOST", raising=False)
    monkeypatch.delenv("LISSN_PORT", raising=False)
    monkeypatch.delenv("LISSN_BASE_URL", raising=False)
    monkeypatch.delenv("LISSN_MAX_EPISODES_PER_SHOW", raising=False)

    config = Config()

    assert config.books_dir == (tmp_path / "data" / "Books").resolve()
    assert config.podcasts_dir == (tmp_path / "data" / "Podcasts").resolve()
    assert config.cache_dir == (tmp_path / "data" / "cache").resolve()
    assert config.cache_db_path == (tmp_path / "data" / "cache" / "lissn_cache.db").resolve()
    assert config.host == "0.0.0.0"
    assert config.port == 8000
    assert config.base_url == "http://localhost:8000"
    assert config.max_episodes_per_show == 2000


def test_config_environment_variable_overrides(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that LISSN_* environment variables correctly override configuration defaults."""
    custom_books = tmp_path / "my_books"
    custom_podcasts = tmp_path / "my_podcasts"
    custom_cache = tmp_path / "my_cache"
    custom_db = custom_cache / "custom.db"

    monkeypatch.setenv("LISSN_BOOKS_DIR", str(custom_books))
    monkeypatch.setenv("LISSN_PODCASTS_DIR", str(custom_podcasts))
    monkeypatch.setenv("LISSN_CACHE_DIR", str(custom_cache))
    monkeypatch.setenv("LISSN_CACHE_DB", str(custom_db))
    monkeypatch.setenv("LISSN_HOST", "127.0.0.1")
    monkeypatch.setenv("LISSN_PORT", "9090")
    monkeypatch.setenv("LISSN_BASE_URL", "https://lissn.example.com")
    monkeypatch.setenv("LISSN_MAX_EPISODES_PER_SHOW", "500")

    config = Config()

    assert config.books_dir == custom_books.resolve()
    assert config.podcasts_dir == custom_podcasts.resolve()
    assert config.cache_dir == custom_cache.resolve()
    assert config.cache_db_path == custom_db.resolve()
    assert config.host == "127.0.0.1"
    assert config.port == 9090
    assert config.base_url == "https://lissn.example.com"
    assert config.max_episodes_per_show == 500


def test_config_json_file_loading(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test reading settings from a JSON configuration file inside config/ directory."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("LISSN_BOOKS_DIR", raising=False)
    monkeypatch.delenv("LISSN_PODCASTS_DIR", raising=False)
    monkeypatch.delenv("LISSN_CACHE_DIR", raising=False)
    monkeypatch.delenv("LISSN_CACHE_DB", raising=False)
    monkeypatch.delenv("LISSN_HOST", raising=False)
    monkeypatch.delenv("LISSN_PORT", raising=False)
    monkeypatch.delenv("LISSN_BASE_URL", raising=False)
    monkeypatch.delenv("LISSN_MAX_EPISODES_PER_SHOW", raising=False)

    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "lissn.json"

    config_data = {
        "books_dir": str(tmp_path / "json_books"),
        "podcasts_dir": str(tmp_path / "json_podcasts"),
        "cache_dir": str(tmp_path / "json_cache"),
        "cache_db_path": str(tmp_path / "json_cache" / "db.sqlite"),
        "host": "0.0.0.0",
        "port": 8080,
        "base_url": "http://192.168.1.50:8080",
        "max_episodes_per_show": 1500,
    }
    config_file.write_text(json.dumps(config_data), encoding="utf-8")

    config = Config()

    assert config.books_dir == (tmp_path / "json_books").resolve()
    assert config.podcasts_dir == (tmp_path / "json_podcasts").resolve()
    assert config.cache_dir == (tmp_path / "json_cache").resolve()
    assert config.cache_db_path == (tmp_path / "json_cache" / "db.sqlite").resolve()
    assert config.port == 8080
    assert config.base_url == "http://192.168.1.50:8080"
    assert config.max_episodes_per_show == 1500


def test_config_ensure_directories(tmp_path: Path) -> None:
    """Test ensure_directories method creates required directories on disk."""
    books = tmp_path / "nested" / "books"
    podcasts = tmp_path / "nested" / "podcasts"
    cache = tmp_path / "nested" / "cache"
    cache_db = cache / "db.sqlite"

    config = Config(
        books_dir=str(books),
        podcasts_dir=str(podcasts),
        cache_dir=str(cache),
        cache_db_path=str(cache_db),
    )

    assert not books.exists()
    assert not podcasts.exists()

    config.ensure_directories()

    assert books.is_dir()
    assert podcasts.is_dir()
    assert cache.is_dir()
