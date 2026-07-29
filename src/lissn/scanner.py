"""
Scanner module for lissn.
Recursively indexes audiobooks and podcasts, calculates audio duration,
locates cover art, computes fuzzy added dates, and caches data in SQLite.
"""

from datetime import datetime, timezone
import hashlib
from pathlib import Path
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

import mutagen

AUDIO_EXTENSIONS = {".mp3", ".m4a", ".m4b", ".aac", ".flac", ".ogg", ".opus", ".wav"}
COVER_NAMES = ["cover.jpg", "cover.jpeg", "cover.png", "folder.jpg", "folder.png", "poster.jpg"]


def generate_show_id(section: str, folder_name: str) -> str:
    """Generate a stable, URL-safe show ID from section and folder name."""
    raw = f"{section}:{folder_name.lower()}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def format_duration(total_seconds: float) -> str:
    """Format total seconds into a readable string like '2h 15m' or '45m 20s'."""
    seconds = int(total_seconds)
    if seconds <= 0:
        return "0m"

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:
        if minutes > 0:
            return f"{hours}h {minutes}m"
        return f"{hours}h"
    elif minutes > 0:
        if secs > 0 and minutes < 5:
            return f"{minutes}m {secs}s"
        return f"{minutes}m"
    else:
        return f"{secs}s"


def format_fuzzy_date(timestamp: float) -> str:
    """Format a POSIX timestamp into a human-readable relative date string."""
    now = datetime.now(timezone.utc)
    added_time = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    diff = now - added_time

    seconds = diff.total_seconds()
    if seconds < 0:
        return "Just now"

    days = int(seconds // 86400)
    hours = int(seconds // 3600)

    if hours < 1:
        return "Just now"
    if hours < 24:
        return "Today"
    if days == 1:
        return "Yesterday"
    if days < 7:
        return f"{days} days ago"
    if days < 30:
        weeks = days // 7
        return f"{weeks} week{'s' if weeks > 1 else ''} ago"
    if days < 365:
        months = days // 30
        return f"{months} month{'s' if months > 1 else ''} ago"

    years = days // 365
    return f"{years} year{'s' if years > 1 else ''} ago"


def get_audio_duration(file_path: Path) -> float:
    """Read audio duration in seconds using mutagen with safe fallback."""
    try:
        audio = mutagen.File(file_path)
        if audio is not None and hasattr(audio, "info") and audio.info is not None:
            if hasattr(audio.info, "length") and audio.info.length:
                return float(audio.info.length)
    except Exception:
        pass
    return 0.0


def find_cover_image(folder_path: Path) -> Optional[Path]:
    """Locate the best available cover image file in the show folder."""
    # Check preferred cover filenames
    for filename in COVER_NAMES:
        candidate = folder_path / filename
        if candidate.is_file():
            return candidate

    # Search for any jpeg/jpg/png file
    for candidate in sorted(folder_path.iterdir()):
        if candidate.is_file() and candidate.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
            return candidate

    return None


def read_description(folder_path: Path) -> str:
    """Extract show description from txt/markdown files in the directory if present."""
    for desc_file in ["description.txt", "info.txt", "README.md", "about.txt"]:
        path = folder_path / desc_file
        if path.is_file():
            try:
                content = path.read_text(encoding="utf-8").strip()
                if content:
                    return content
            except Exception:
                pass
    return ""


class ScannerCache:
    """SQLite cache manager for indexed media shows and episodes."""

    def __init__(self, db_path: Path) -> None:
        """Initialize database connection and schema."""
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS shows (
                    show_id TEXT PRIMARY KEY,
                    section TEXT NOT NULL,
                    title TEXT NOT NULL,
                    folder_path TEXT NOT NULL,
                    cover_path TEXT,
                    total_duration REAL NOT NULL,
                    formatted_duration TEXT NOT NULL,
                    added_timestamp REAL NOT NULL,
                    fuzzy_added_date TEXT NOT NULL,
                    description TEXT,
                    episode_count INTEGER NOT NULL,
                    updated_at REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS episodes (
                    episode_id TEXT PRIMARY KEY,
                    show_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    duration REAL NOT NULL,
                    formatted_duration TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    added_timestamp REAL NOT NULL,
                    FOREIGN KEY(show_id) REFERENCES shows(show_id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_shows_section ON shows(section);
                CREATE INDEX IF NOT EXISTS idx_episodes_show_id ON episodes(show_id);
                """
            )

    def save_show(self, show_data: Dict[str, Any], episodes: List[Dict[str, Any]]) -> None:
        """Save show and its associated episodes into the database cache."""
        now = datetime.now(timezone.utc).timestamp()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO shows (
                    show_id, section, title, folder_path, cover_path,
                    total_duration, formatted_duration, added_timestamp,
                    fuzzy_added_date, description, episode_count, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    show_data["show_id"],
                    show_data["section"],
                    show_data["title"],
                    show_data["folder_path"],
                    show_data.get("cover_path"),
                    show_data["total_duration"],
                    show_data["formatted_duration"],
                    show_data["added_timestamp"],
                    show_data["fuzzy_added_date"],
                    show_data.get("description", ""),
                    len(episodes),
                    now,
                ),
            )

            conn.execute("DELETE FROM episodes WHERE show_id = ?", (show_data["show_id"],))
            for ep in episodes:
                conn.execute(
                    """
                    INSERT INTO episodes (
                        episode_id, show_id, title, filename, file_path,
                        duration, formatted_duration, file_size, added_timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        ep["episode_id"],
                        show_data["show_id"],
                        ep["title"],
                        ep["filename"],
                        ep["file_path"],
                        ep["duration"],
                        ep["formatted_duration"],
                        ep["file_size"],
                        ep["added_timestamp"],
                    ),
                )

    def get_all_shows(self, section: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve all cached shows, optionally filtered by section."""
        with self._get_connection() as conn:
            if section:
                cursor = conn.execute(
                    "SELECT * FROM shows WHERE section = ? ORDER BY added_timestamp DESC",
                    (section.lower(),),
                )
            else:
                cursor = conn.execute("SELECT * FROM shows ORDER BY added_timestamp DESC")
            return [dict(row) for row in cursor.fetchall()]

    def get_show(self, show_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve single show data with associated episodes."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM shows WHERE show_id = ?", (show_id,))
            row = cursor.fetchone()
            if not row:
                return None
            show = dict(row)

            ep_cursor = conn.execute(
                "SELECT * FROM episodes WHERE show_id = ? ORDER BY filename ASC", (show_id,)
            )
            show["episodes"] = [dict(ep) for ep in ep_cursor.fetchall()]
            return show

    def clear(self) -> None:
        """Clear all cached show and episode entries."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM episodes")
            conn.execute("DELETE FROM shows")


class LibraryScanner:
    """Scans Books and Podcasts folders and populates the SQLite cache."""

    def __init__(self, books_dir: Path, podcasts_dir: Path, db_path: Path) -> None:
        self.books_dir = books_dir
        self.podcasts_dir = podcasts_dir
        self.cache = ScannerCache(db_path)

    def scan_folder(self, section: str, root_dir: Path) -> List[Dict[str, Any]]:
        """Scan a top-level media directory (Books or Podcasts)."""
        scanned_shows = []
        if not root_dir.exists() or not root_dir.is_dir():
            return scanned_shows

        # Every child directory under root_dir is a show
        for show_dir in sorted(root_dir.iterdir()):
            if not show_dir.is_dir() or show_dir.name.startswith("."):
                continue

            show_id = generate_show_id(section, show_dir.name)
            cover_path = find_cover_image(show_dir)
            description = read_description(show_dir)

            audio_files = []
            for item in sorted(show_dir.rglob("*")):
                if item.is_file() and item.suffix.lower() in AUDIO_EXTENSIONS:
                    audio_files.append(item)

            if not audio_files:
                continue

            episodes = []
            total_duration = 0.0
            earliest_timestamp = float("inf")

            for idx, audio_path in enumerate(audio_files, 1):
                stat = audio_path.stat()
                mtime = stat.st_mtime
                if mtime < earliest_timestamp:
                    earliest_timestamp = mtime

                duration = get_audio_duration(audio_path)
                total_duration += duration

                title = audio_path.stem
                ep_id = f"{show_id}_ep_{idx}"
                episodes.append(
                    {
                        "episode_id": ep_id,
                        "title": title,
                        "filename": audio_path.name,
                        "file_path": str(audio_path.resolve()),
                        "duration": duration,
                        "formatted_duration": format_duration(duration),
                        "file_size": stat.st_size,
                        "added_timestamp": mtime,
                    }
                )

            if earliest_timestamp == float("inf"):
                earliest_timestamp = show_dir.stat().st_mtime

            show_data = {
                "show_id": show_id,
                "section": section,
                "title": show_dir.name,
                "folder_path": str(show_dir.resolve()),
                "cover_path": str(cover_path.resolve()) if cover_path else None,
                "total_duration": total_duration,
                "formatted_duration": format_duration(total_duration),
                "added_timestamp": earliest_timestamp,
                "fuzzy_added_date": format_fuzzy_date(earliest_timestamp),
                "description": description,
            }

            self.cache.save_show(show_data, episodes)
            scanned_shows.append(show_data)

        return scanned_shows

    def scan_all(self) -> Dict[str, Any]:
        """Scan both Books and Podcasts sections."""
        books = self.scan_folder("books", self.books_dir)
        podcasts = self.scan_folder("podcasts", self.podcasts_dir)
        return {"books": books, "podcasts": podcasts, "total": len(books) + len(podcasts)}
