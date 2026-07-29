"""
Configuration manager for lissn.
Loads settings from lissn.json (or config/lissn.json / config/lissn.example.json)
with environment variable overrides.
"""

from pathlib import Path
import json
import os
from typing import Optional


class Config:
    """Application configuration container."""

    def __init__(
        self,
        books_dir: Optional[str] = None,
        podcasts_dir: Optional[str] = None,
        cache_dir: Optional[str] = None,
        cache_db_path: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        base_url: Optional[str] = None,
    ) -> None:
        """Initialize configuration with file/env overrides and defaults."""
        base_dir = Path.cwd()

        # Candidates for configuration JSON file (prioritizing config/lissn.json)
        config_candidates = [
            base_dir / "config" / "lissn.json",
            base_dir / "config" / "lissn.example.json",
        ]

        json_config = {}
        for candidate in config_candidates:
            if candidate.is_file():
                try:
                    with open(candidate, "r", encoding="utf-8") as f:
                        json_config = json.load(f)
                    break
                except Exception:
                    pass

        # Resolve Books path
        raw_books = (
            books_dir
            or os.getenv("LISSN_BOOKS_DIR")
            or json_config.get("books_dir")
            or str(base_dir / "data" / "Books")
        )
        self.books_dir: Path = Path(raw_books).resolve()

        # Resolve Podcasts path
        raw_podcasts = (
            podcasts_dir
            or os.getenv("LISSN_PODCASTS_DIR")
            or json_config.get("podcasts_dir")
            or str(base_dir / "data" / "Podcasts")
        )
        self.podcasts_dir: Path = Path(raw_podcasts).resolve()

        # Resolve Cache Directory path
        raw_cache_dir = (
            cache_dir
            or os.getenv("LISSN_CACHE_DIR")
            or json_config.get("cache_dir")
            or str(base_dir / "data" / "cache")
        )
        self.cache_dir: Path = Path(raw_cache_dir).resolve()

        # Resolve Cache DB path
        raw_cache_db = (
            cache_db_path
            or os.getenv("LISSN_CACHE_DB")
            or json_config.get("cache_db_path")
            or str(self.cache_dir / "lissn_cache.db")
        )
        self.cache_db_path: Path = Path(raw_cache_db).resolve()

        self.host: str = host or os.getenv("LISSN_HOST") or json_config.get("host") or "0.0.0.0"
        self.port: int = int(port or os.getenv("LISSN_PORT") or json_config.get("port") or 8000)
        self.base_url: str = (
            base_url
            or os.getenv("LISSN_BASE_URL")
            or json_config.get("base_url")
            or f"http://localhost:{self.port}"
        )

    def ensure_directories(self) -> None:
        """Ensure media and cache directories exist on disk."""
        self.books_dir.mkdir(parents=True, exist_ok=True)
        self.podcasts_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_db_path.parent.mkdir(parents=True, exist_ok=True)
