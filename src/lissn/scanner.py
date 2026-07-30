"""
Scanner module for lissn.
Recursively indexes audiobooks and podcasts, calculates audio duration,
locates cover art, computes fuzzy added dates, reads notes.md from cache_dir,
and caches show data in SQLite.
"""

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import sqlite3
from typing import Any, Dict, List, Optional

import markdown
import mutagen
import yaml

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


def format_file_size(size_bytes: int) -> str:
    """Format size in bytes to human readable string (e.g. '15.4 MB', '1.2 GB')."""
    if size_bytes <= 0:
        return "0 B"
    size = float(size_bytes)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size < 1024.0 or unit == "TB":
            if unit == "B":
                return f"{int(size)} B"
            elif unit == "KB":
                return f"{size:.1f} KB"
            else:
                return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size_bytes} B"


def get_audio_bitrate(file_path: Path, file_size: int, duration: float) -> int:
    """Calculate or read audio bitrate in kbps."""
    try:
        audio = mutagen.File(file_path)
        if audio is not None and hasattr(audio, "info") and audio.info is not None:
            if hasattr(audio.info, "bitrate") and audio.info.bitrate:
                br = int(audio.info.bitrate)
                if br > 1000:
                    return int(round(br / 1000.0))
                elif br > 0:
                    return br
    except Exception:
        pass

    if duration > 0 and file_size > 0:
        kbps = int(round((file_size * 8) / (duration * 1000)))
        return kbps
    return 0


def format_bitrate(bitrate_kbps: int) -> str:
    """Format bitrate in kbps to human readable string (e.g. '128 kbps')."""
    if bitrate_kbps > 0:
        return f"{bitrate_kbps} kbps"
    return "N/A"


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


def decode_metadata_text(val: Any) -> str:
    """Safely extract string from Mutagen tag values and fix Latin-1/UTF-8 double-encoding."""
    if not val:
        return ""
    if isinstance(val, (list, tuple)) and len(val) > 0:
        val = val[0]
    if hasattr(val, "text") and isinstance(val.text, (list, tuple)) and len(val.text) > 0:
        val = val.text[0]

    s = str(val).strip()
    if not s:
        return ""

    # Try fixing double-encoded UTF-8 strings (common in ID3v2 latin-1 frames storing UTF-8 bytes)
    try:
        if any(ord(c) >= 0x80 for c in s):
            latin1_bytes = s.encode("latin-1")
            decoded = latin1_bytes.decode("utf-8")
            if decoded:
                s = decoded
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass
    return s


def get_audio_title(file_path: Path) -> str:
    """
    Extract audio track title from ID3 / metadata tags with safe UTF-8 decoding.
    Falls back to unquoted filename stem if metadata tag is missing or empty.
    """
    try:
        audio = mutagen.File(file_path)
        if audio is not None and hasattr(audio, "tags") and audio.tags:
            # Check common tag keys for track title
            for key in ["TIT2", "title", "TITLE", "\xa9nam", "TIT1"]:
                val = audio.tags.get(key)
                if val:
                    title_str = decode_metadata_text(val)
                    if title_str:
                        return title_str
    except Exception:
        pass

    from urllib.parse import unquote
    return unquote(file_path.stem)



IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def find_cover_image(folder_path: Path) -> Optional[Path]:
    """Locate the best available cover image file in the show folder."""
    for filename in COVER_NAMES:
        candidate = folder_path / filename
        if candidate.is_file():
            return candidate

    for candidate in sorted(folder_path.iterdir()):
        if candidate.is_file() and candidate.suffix.lower() in IMAGE_EXTENSIONS:
            return candidate

    return None


def list_show_images(folder_path: Path) -> List[Dict[str, Any]]:
    """List all available image files in the show folder."""
    images = []
    if not folder_path.exists() or not folder_path.is_dir():
        return images

    for item in sorted(folder_path.iterdir()):
        if item.is_file() and item.suffix.lower() in IMAGE_EXTENSIONS:
            stat = item.stat()
            images.append(
                {
                    "filename": item.name,
                    "file_path": str(item.resolve()),
                    "size": stat.st_size,
                    "formatted_size": format_file_size(stat.st_size),
                }
            )
    return images


def get_or_create_notes(cache_dir: Path, section: str, show_name: str) -> Dict[str, Any]:
    """
    Locate or create notes.md inside cache_dir / section / show_name / notes.md.
    Parses frontmatter for author, title, podcast_name, and converts markdown description.
    """
    show_cache_dir = cache_dir / section / show_name
    show_cache_dir.mkdir(parents=True, exist_ok=True)

    notes_file = show_cache_dir / "notes.md"

    if not notes_file.exists():
        if section == "books":
            default_content = f"""---
title: "{show_name}"
author: "Unknown Author"
---

# {show_name}

Add book description in markdown format here.
"""
        else:
            default_content = f"""---
podcast_name: "{show_name}"
publisher: "Podcast Publisher"
---

# {show_name}

Add podcast description in markdown format here.
"""
        notes_file.write_text(default_content, encoding="utf-8")

    raw_text = notes_file.read_text(encoding="utf-8").strip()

    title = show_name
    author = ""
    publisher = ""
    podcast_name = show_name if section == "podcasts" else ""
    body = raw_text

    if raw_text.startswith("---"):
        parts = raw_text.split("---", 2)
        if len(parts) >= 3:
            yaml_block = parts[1].strip()
            body = parts[2].strip()
            try:
                meta = yaml.safe_load(yaml_block) or {}
                if isinstance(meta, dict):
                    if meta.get("title"):
                        title = str(meta["title"]).strip()
                    if meta.get("podcast_name"):
                        podcast_name = str(meta["podcast_name"]).strip()
                    if section == "books":
                        if meta.get("author"):
                            author = str(meta["author"]).strip()
                    else:
                        if meta.get("publisher"):
                            publisher = str(meta["publisher"]).strip()
                        elif meta.get("author"):
                            publisher = str(meta["author"]).strip()
            except Exception:
                pass

    html_description = markdown.markdown(body, extensions=["extra"]) if body else ""

    return {
        "title": title,
        "author": author,
        "publisher": publisher,
        "podcast_name": podcast_name,
        "description": body,
        "description_html": html_description,
        "notes_path": str(notes_file.resolve()),
    }


class ScannerCache:
    """SQLite cache manager for indexed media shows and episodes."""

    def __init__(self, db_path: Path) -> None:
        """Initialize database connection and schema."""
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS shows (
                    show_id TEXT PRIMARY KEY,
                    section TEXT NOT NULL,
                    title TEXT NOT NULL,
                    author TEXT,
                    publisher TEXT DEFAULT '',
                    podcast_name TEXT,
                    folder_path TEXT NOT NULL,
                    cover_path TEXT,
                    total_duration REAL NOT NULL,
                    formatted_duration TEXT NOT NULL,
                    total_file_size INTEGER DEFAULT 0,
                    formatted_total_file_size TEXT DEFAULT '',
                    added_timestamp REAL NOT NULL,
                    fuzzy_added_date TEXT NOT NULL,
                    description TEXT,
                    description_html TEXT,
                    notes_path TEXT,
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
                    formatted_file_size TEXT DEFAULT '',
                    bitrate INTEGER DEFAULT 0,
                    formatted_bitrate TEXT DEFAULT '',
                    added_timestamp REAL NOT NULL,
                    FOREIGN KEY(show_id) REFERENCES shows(show_id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_shows_section ON shows(section);
                CREATE INDEX IF NOT EXISTS idx_episodes_show_id ON episodes(show_id);
                """
            )
            # Automatic schema migrations for existing database files
            cursor = conn.execute("PRAGMA table_info(shows)")
            show_cols = {row["name"] for row in cursor.fetchall()}
            if "total_file_size" not in show_cols:
                conn.execute("ALTER TABLE shows ADD COLUMN total_file_size INTEGER DEFAULT 0")
            if "formatted_total_file_size" not in show_cols:
                conn.execute("ALTER TABLE shows ADD COLUMN formatted_total_file_size TEXT DEFAULT ''")
            if "publisher" not in show_cols:
                conn.execute("ALTER TABLE shows ADD COLUMN publisher TEXT DEFAULT ''")

            cursor = conn.execute("PRAGMA table_info(episodes)")
            ep_cols = {row["name"] for row in cursor.fetchall()}
            if "formatted_file_size" not in ep_cols:
                conn.execute("ALTER TABLE episodes ADD COLUMN formatted_file_size TEXT DEFAULT ''")
            if "bitrate" not in ep_cols:
                conn.execute("ALTER TABLE episodes ADD COLUMN bitrate INTEGER DEFAULT 0")
            if "formatted_bitrate" not in ep_cols:
                conn.execute("ALTER TABLE episodes ADD COLUMN formatted_bitrate TEXT DEFAULT ''")

            # Clean up section metadata so podcasts only use publisher and books only use author
            conn.execute("UPDATE shows SET publisher = author WHERE section = 'podcasts' AND (publisher IS NULL OR publisher = '') AND author IS NOT NULL AND author != ''")
            conn.execute("UPDATE shows SET author = '' WHERE section = 'podcasts'")
            conn.execute("UPDATE shows SET publisher = '' WHERE section = 'books'")

    def save_show(self, show_data: Dict[str, Any], episodes: List[Dict[str, Any]]) -> None:
        """Save show and its associated episodes into the database cache."""
        now = datetime.now(timezone.utc).timestamp()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO shows (
                    show_id, section, title, author, publisher, podcast_name, folder_path, cover_path,
                    total_duration, formatted_duration, total_file_size, formatted_total_file_size,
                    added_timestamp, fuzzy_added_date, description, description_html, notes_path,
                    episode_count, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    show_data["show_id"],
                    show_data["section"],
                    show_data["title"],
                    show_data.get("author", ""),
                    show_data.get("publisher", ""),
                    show_data.get("podcast_name", ""),
                    show_data["folder_path"],
                    show_data.get("cover_path"),
                    show_data["total_duration"],
                    show_data["formatted_duration"],
                    show_data.get("total_file_size", 0),
                    show_data.get("formatted_total_file_size", ""),
                    show_data["added_timestamp"],
                    show_data["fuzzy_added_date"],
                    show_data.get("description", ""),
                    show_data.get("description_html", ""),
                    show_data.get("notes_path", ""),
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
                        duration, formatted_duration, file_size, formatted_file_size,
                        bitrate, formatted_bitrate, added_timestamp
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                        ep.get("formatted_file_size", ""),
                        ep.get("bitrate", 0),
                        ep.get("formatted_bitrate", ""),
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

    def get_episodes_map(self, show_id: str) -> Dict[str, Dict[str, Any]]:
        """Retrieve map of resolved file_path -> episode data dict for a given show_id."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM episodes WHERE show_id = ?", (show_id,)
            )
            return {row["file_path"]: dict(row) for row in cursor.fetchall()}

    def prune_deleted_shows(self, active_show_ids: List[str]) -> None:
        """Remove shows and episodes from database cache if no longer present on disk."""
        with self._get_connection() as conn:
            if not active_show_ids:
                conn.execute("DELETE FROM episodes")
                conn.execute("DELETE FROM shows")
            else:
                placeholders = ",".join(["?"] * len(active_show_ids))
                conn.execute(f"DELETE FROM episodes WHERE show_id NOT IN ({placeholders})", active_show_ids)
                conn.execute(f"DELETE FROM shows WHERE show_id NOT IN ({placeholders})", active_show_ids)

    def get_all_authors(self) -> List[str]:
        """Retrieve sorted list of distinct authors across all book shows."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT DISTINCT author FROM shows WHERE section = 'books' AND author IS NOT NULL AND author != '' ORDER BY author ASC"
            )
            return [row["author"] for row in cursor.fetchall()]

    def get_all_publishers(self) -> List[str]:
        """Retrieve sorted list of distinct publishers across all podcast shows."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT DISTINCT publisher FROM shows WHERE section = 'podcasts' AND publisher IS NOT NULL AND publisher != '' ORDER BY publisher ASC"
            )
            return [row["publisher"] for row in cursor.fetchall()]

    def clear(self) -> None:
        """Clear all cached show and episode entries."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM episodes")
            conn.execute("DELETE FROM shows")


class LibraryScanner:
    """Scans Books and Podcasts folders and populates the SQLite cache."""

    def __init__(
        self,
        books_dir: Path,
        podcasts_dir: Path,
        cache_dir: Path,
        db_path: Path,
        max_episodes_per_show: int = 2000,
    ) -> None:
        self.books_dir = books_dir
        self.podcasts_dir = podcasts_dir
        self.cache_dir = cache_dir
        self.max_episodes_per_show = max_episodes_per_show
        self.cache = ScannerCache(db_path)

    def scan_folder(self, section: str, root_dir: Path, force: bool = False) -> List[Dict[str, Any]]:
        """Scan a top-level media directory (Books or Podcasts)."""
        scanned_shows = []
        if not root_dir.exists() or not root_dir.is_dir():
            return scanned_shows

        for show_dir in sorted(root_dir.iterdir()):
            if not show_dir.is_dir() or show_dir.name.startswith("."):
                continue

            show_id = generate_show_id(section, show_dir.name)
            cover_path = find_cover_image(show_dir)

            # Load or create notes.md in cache directory
            notes_info = get_or_create_notes(
                cache_dir=self.cache_dir,
                section=section,
                show_name=show_dir.name,
            )

            audio_files = []
            for item in sorted(show_dir.rglob("*")):
                if item.is_file() and item.suffix.lower() in AUDIO_EXTENSIONS:
                    audio_files.append(item)

            if not audio_files:
                continue

            # Limit number of episodes per show based on max_episodes_per_show setting
            audio_files = audio_files[: self.max_episodes_per_show]

            # Fetch existing cached episode metadata for incremental scanning
            cached_episodes_map = {} if force else self.cache.get_episodes_map(show_id)

            episodes = []
            total_duration = 0.0
            total_file_size = 0
            earliest_timestamp = float("inf")

            for idx, audio_path in enumerate(audio_files, 1):
                stat = audio_path.stat()
                mtime = stat.st_mtime
                file_size = stat.st_size
                if mtime < earliest_timestamp:
                    earliest_timestamp = mtime

                resolved_path_str = str(audio_path.resolve())
                cached_ep = cached_episodes_map.get(resolved_path_str)

                # Incremental cache check: if file size and mtime match, reuse cached episode metadata
                if (
                    cached_ep
                    and cached_ep.get("file_size") == file_size
                    and abs(cached_ep.get("added_timestamp", 0) - mtime) < 0.001
                ):
                    duration = float(cached_ep.get("duration", 0.0))
                    bitrate_kbps = int(cached_ep.get("bitrate", 0))
                    title = str(cached_ep.get("title", ""))
                else:
                    duration = get_audio_duration(audio_path)
                    bitrate_kbps = get_audio_bitrate(audio_path, file_size, duration)
                    title = get_audio_title(audio_path)

                total_duration += duration
                total_file_size += file_size

                ep_id = f"{show_id}_ep_{idx}"
                rel_filename = str(audio_path.relative_to(show_dir))
                episodes.append(
                    {
                        "episode_id": ep_id,
                        "title": title,
                        "filename": rel_filename,
                        "file_path": resolved_path_str,
                        "duration": duration,
                        "formatted_duration": format_duration(duration),
                        "file_size": file_size,
                        "formatted_file_size": format_file_size(file_size),
                        "bitrate": bitrate_kbps,
                        "formatted_bitrate": format_bitrate(bitrate_kbps),
                        "added_timestamp": mtime,
                    }
                )

            # If track title is the same for all episodes, change track names to "Track 1", "Track 2", etc.
            if len(episodes) > 1 and len({ep["title"].strip() for ep in episodes}) == 1:
                for idx, ep in enumerate(episodes, 1):
                    ep["title"] = f"Track {idx}"

            if earliest_timestamp == float("inf"):
                earliest_timestamp = show_dir.stat().st_mtime

            # Derive title: use notes.md title or podcast_name if custom, else folder name
            display_title = notes_info["title"] or show_dir.name

            show_data = {
                "show_id": show_id,
                "section": section,
                "title": display_title,
                "author": notes_info.get("author", "") if section == "books" else "",
                "publisher": notes_info.get("publisher", "") if section == "podcasts" else "",
                "podcast_name": notes_info.get("podcast_name", display_title),
                "folder_path": str(show_dir.resolve()),
                "cover_path": str(cover_path.resolve()) if cover_path else None,
                "total_duration": total_duration,
                "formatted_duration": format_duration(total_duration),
                "total_file_size": total_file_size,
                "formatted_total_file_size": format_file_size(total_file_size),
                "added_timestamp": earliest_timestamp,
                "fuzzy_added_date": format_fuzzy_date(earliest_timestamp),
                "description": notes_info.get("description", ""),
                "description_html": notes_info.get("description_html", ""),
                "notes_path": notes_info.get("notes_path", ""),
            }

            self.cache.save_show(show_data, episodes)
            scanned_shows.append(show_data)

        return scanned_shows

    def scan_all(self, force: bool = False) -> Dict[str, Any]:
        """Scan both Books and Podcasts sections, optionally forcing full metadata re-parse."""
        books = self.scan_folder("books", self.books_dir, force=force)
        podcasts = self.scan_folder("podcasts", self.podcasts_dir, force=force)
        active_ids = [s["show_id"] for s in books + podcasts]
        self.cache.prune_deleted_shows(active_ids)
        return {"books": books, "podcasts": podcasts, "total": len(books) + len(podcasts)}

    def update_show_metadata(
        self, show_id: str, title: str, author: str = "", description: str = "", publisher: str = ""
    ) -> Optional[Dict[str, Any]]:
        """Update title, author, publisher, and description for a show and re-save notes.md."""
        show = self.cache.get_show(show_id)
        if not show:
            return None

        notes_path_str = show.get("notes_path")
        if notes_path_str and Path(notes_path_str).parent.exists():
            notes_file = Path(notes_path_str)
        else:
            folder_name = Path(show["folder_path"]).name
            notes_file = self.cache_dir / show["section"] / folder_name / "notes.md"
            notes_file.parent.mkdir(parents=True, exist_ok=True)

        section = show["section"]
        title = title.strip()
        description = description.strip()

        if section == "books":
            author = author.strip()
            publisher = ""
            yaml_header = f'---\ntitle: "{title}"\nauthor: "{author}"\n---'
        else:
            publisher = publisher.strip() or author.strip()
            author = ""
            yaml_header = f'---\npodcast_name: "{title}"\npublisher: "{publisher}"\n---'

        notes_content = f"{yaml_header}\n\n{description}\n"
        notes_file.write_text(notes_content, encoding="utf-8")

        html_description = markdown.markdown(description, extensions=["extra"]) if description else ""

        show["title"] = title
        show["author"] = author
        show["publisher"] = publisher
        if section == "podcasts":
            show["podcast_name"] = title
        show["description"] = description
        show["description_html"] = html_description
        show["notes_path"] = str(notes_file.resolve())

        self.cache.save_show(show, show["episodes"])
        return show

    def update_show_cover(self, show_id: str, new_cover_path: Path) -> Optional[Dict[str, Any]]:
        """Update cover_path for a show in database cache."""
        show = self.cache.get_show(show_id)
        if not show:
            return None

        show["cover_path"] = str(new_cover_path.resolve())
        self.cache.save_show(show, show["episodes"])
        return show

