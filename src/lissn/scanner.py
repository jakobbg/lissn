"""
Scanner module for lissn.
Recursively indexes audiobooks and podcasts, calculates audio duration,
locates cover art, computes fuzzy added dates, and caches show data in SQLite.
"""

from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import logging
from pathlib import Path, PurePath
import re
import sqlite3
import time
from typing import Any, Dict, List, Optional, Tuple, Union

import markdown
import mutagen

logger = logging.getLogger("lissn.scanner")

AUDIO_EXTENSIONS = {
    ".mp3",
    ".m4a",
    ".m4b",
    ".mp4",
    ".m4v",
    ".m4r",
    ".m4p",
    ".aac",
    ".flac",
    ".ogg",
    ".oga",
    ".opus",
    ".wav",
    ".wma",
    ".aiff",
    ".aif",
    ".alac",
    ".webm",
    ".mp2",
    ".caf",
    ".wv",
    ".ape",
}
COVER_NAMES = ["cover.jpg", "cover.jpeg", "cover.png", "folder.jpg", "folder.png", "poster.jpg"]


def natural_sort_key(s: str) -> Tuple[Tuple[Union[int, str], ...], str]:
    """
    Generate a natural sort key for a string.
    Splits string into numeric and non-numeric tokens so numbers sort numerically.
    Includes the lowercased original string as a tie-breaker.
    """
    s_str = str(s)
    tokens = tuple(
        int(text) if text.isdigit() else text.lower()
        for text in re.split(r"(\d+)", s_str)
    )
    return (tokens, s_str.lower())


def episode_sort_key(
    filename_or_path: Union[str, Path, PurePath]
) -> Tuple[Tuple[Tuple[Union[int, str], ...], str], Tuple[Tuple[Union[int, str], ...], str]]:
    """
    Generate sort key for an episode relative file path:
    1. Primary sort: Folder path components (folder first, naturally sorted).
       Files in root show directory have empty folder tuple () and sort before subfolders.
    2. Secondary sort: Filename in folder (naturally sorted).
    """
    norm_path = str(filename_or_path).replace("\\", "/")
    p = PurePath(norm_path)
    folder_parts = p.parts[:-1]
    file_name = p.parts[-1] if p.parts else ""

    folder_key = tuple(natural_sort_key(part) for part in folder_parts)
    file_key = natural_sort_key(file_name)

    return (folder_key, file_key)



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
    raw_title = ""
    try:
        audio = mutagen.File(file_path)
        if audio is not None and hasattr(audio, "tags") and audio.tags:
            # Check common tag keys for track title
            for key in ["TIT2", "title", "TITLE", "\xa9nam", "TIT1"]:
                val = audio.tags.get(key)
                if val:
                    title_str = decode_metadata_text(val)
                    if title_str:
                        raw_title = title_str
                        break
    except Exception:
        pass

    if not raw_title:
        from urllib.parse import unquote
        raw_title = unquote(file_path.stem)

    return raw_title.strip()


def resolve_unique_track_titles(episodes_info: List[Dict[str, Any]]) -> List[str]:
    """
    Resolve unique track titles for a list of episode info dicts in a show.
    Each episode_info dict has:
      - 'tag_title': title from tags (or stem if no tag)
      - 'stem': filename stem (filename without extension)
      - 'subfolder': subfolder relative string (or empty string)

    If 2 or more tracks share the same primary title (<subfolder>/<tag_title>),
    they fall back to using <subfolder>/<stem>.
    Final pass ensures zero duplicate track titles within the show.
    """
    primary_titles = []
    fallback_titles = []
    for item in episodes_info:
        subfolder = item.get("subfolder", "").strip()
        tag_title = item.get("tag_title", "").strip()
        stem = item.get("stem", "").strip()

        p_title = f"{subfolder}/{tag_title}" if subfolder else tag_title
        f_title = f"{subfolder}/{stem}" if subfolder else stem

        primary_titles.append(p_title)
        fallback_titles.append(f_title)

    p_counts = Counter(primary_titles)

    chosen_titles = []
    for i in range(len(episodes_info)):
        if p_counts[primary_titles[i]] > 1:
            chosen_titles.append(fallback_titles[i])
        else:
            chosen_titles.append(primary_titles[i])

    # Check if chosen_titles still contain any duplicates
    c_counts = Counter(chosen_titles)
    for i in range(len(episodes_info)):
        if c_counts[chosen_titles[i]] > 1 and chosen_titles[i] != fallback_titles[i]:
            chosen_titles[i] = fallback_titles[i]

    # Final safety pass: guarantee absolute uniqueness across the show
    final_titles = []
    final_counts = Counter(chosen_titles)
    seen_so_far = Counter()
    for title in chosen_titles:
        seen_so_far[title] += 1
        if final_counts[title] > 1:
            count = seen_so_far[title]
            if count == 1:
                final_titles.append(title)
            else:
                final_titles.append(f"{title} ({count})")
        else:
            final_titles.append(title)

    return final_titles



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
                    is_custom_title INTEGER DEFAULT 0,
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
            if "cover_data" not in show_cols:
                conn.execute("ALTER TABLE shows ADD COLUMN cover_data BLOB")
            if "cover_mime" not in show_cols:
                conn.execute("ALTER TABLE shows ADD COLUMN cover_mime TEXT DEFAULT ''")
            if "cover_filename" not in show_cols:
                conn.execute("ALTER TABLE shows ADD COLUMN cover_filename TEXT DEFAULT ''")

            cursor = conn.execute("PRAGMA table_info(episodes)")
            ep_cols = {row["name"] for row in cursor.fetchall()}
            if "formatted_file_size" not in ep_cols:
                conn.execute("ALTER TABLE episodes ADD COLUMN formatted_file_size TEXT DEFAULT ''")
            if "bitrate" not in ep_cols:
                conn.execute("ALTER TABLE episodes ADD COLUMN bitrate INTEGER DEFAULT 0")
            if "formatted_bitrate" not in ep_cols:
                conn.execute("ALTER TABLE episodes ADD COLUMN formatted_bitrate TEXT DEFAULT ''")
            if "is_custom_title" not in ep_cols:
                conn.execute("ALTER TABLE episodes ADD COLUMN is_custom_title INTEGER DEFAULT 0")

            # Clean up section metadata so podcasts only use publisher and books only use author
            if "author" in show_cols and "publisher" in show_cols:
                conn.execute("UPDATE shows SET publisher = author WHERE section = 'podcasts' AND (publisher IS NULL OR publisher = '') AND author IS NOT NULL AND author != ''")
                conn.execute("UPDATE shows SET author = '' WHERE section = 'podcasts'")
                conn.execute("UPDATE shows SET publisher = '' WHERE section = 'books'")

    def save_show(self, show_data: Dict[str, Any], episodes: List[Dict[str, Any]]) -> None:
        """Save show and its associated episodes into the database cache."""
        now = datetime.now(timezone.utc).timestamp()
        sorted_episodes = sorted(
            episodes,
            key=lambda ep: episode_sort_key(ep.get("filename") or ep.get("title") or ""),
        )
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO shows (
                    show_id, section, title, author, publisher, podcast_name, folder_path, cover_path,
                    total_duration, formatted_duration, total_file_size, formatted_total_file_size,
                    added_timestamp, fuzzy_added_date, description, description_html, notes_path,
                    cover_data, cover_mime, cover_filename, episode_count, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    show_data.get("cover_data"),
                    show_data.get("cover_mime", ""),
                    show_data.get("cover_filename", ""),
                    len(episodes),
                    now,
                ),
            )

            conn.execute("DELETE FROM episodes WHERE show_id = ?", (show_data["show_id"],))
            for ep in sorted_episodes:
                conn.execute(
                    """
                    INSERT INTO episodes (
                        episode_id, show_id, title, filename, file_path,
                        duration, formatted_duration, file_size, formatted_file_size,
                        bitrate, formatted_bitrate, added_timestamp, is_custom_title
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                        ep.get("is_custom_title", 0),
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
            shows = []
            for row in cursor.fetchall():
                d = dict(row)
                d.pop("cover_data", None)
                shows.append(d)
            return shows

    def get_show(self, show_id: str, include_cover_data: bool = False) -> Optional[Dict[str, Any]]:
        """Retrieve single show data with associated episodes."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM shows WHERE show_id = ?", (show_id,))
            row = cursor.fetchone()
            if not row:
                return None
            show = dict(row)
            if not include_cover_data:
                show.pop("cover_data", None)

            ep_cursor = conn.execute(
                "SELECT * FROM episodes WHERE show_id = ?", (show_id,)
            )
            episodes = [dict(ep) for ep in ep_cursor.fetchall()]
            episodes.sort(key=lambda ep: episode_sort_key(ep.get("filename") or ep.get("title") or ""))
            show["episodes"] = episodes
            return show

    def get_show_cover_data(self, show_id: str) -> Optional[Tuple[bytes, str]]:
        """Retrieve binary cover_data BLOB and cover_mime string for a given show_id."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT cover_data, cover_mime FROM shows WHERE show_id = ?", (show_id,))
            row = cursor.fetchone()
            if row and row["cover_data"]:
                return row["cover_data"], row["cover_mime"] or "image/jpeg"
            return None

    def get_episodes_map(self, show_id: str) -> Dict[str, Dict[str, Any]]:
        """Retrieve map of resolved file_path -> episode data dict for a given show_id."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM episodes WHERE show_id = ?", (show_id,)
            )
            return {row["file_path"]: dict(row) for row in cursor.fetchall()}

    def update_episode_title(self, show_id: str, episode_id: str, new_title: str) -> Optional[Dict[str, Any]]:
        """Update track/episode title in SQLite database and return updated episode dictionary."""
        new_title = new_title.strip()
        if not new_title:
            return None
        with self._get_connection() as conn:
            dup_cursor = conn.execute(
                "SELECT episode_id FROM episodes WHERE show_id = ? AND LOWER(title) = LOWER(?) AND episode_id != ?",
                (show_id, new_title, episode_id),
            )
            if dup_cursor.fetchone():
                raise ValueError(f"Track title '{new_title}' already exists in this show")

            cursor = conn.execute(
                "UPDATE episodes SET title = ?, is_custom_title = 1 WHERE show_id = ? AND episode_id = ?",
                (new_title, show_id, episode_id),
            )
            if cursor.rowcount == 0:
                return None
            ep_cursor = conn.execute(
                "SELECT * FROM episodes WHERE show_id = ? AND episode_id = ?",
                (show_id, episode_id),
            )
            ep_row = ep_cursor.fetchone()
            return dict(ep_row) if ep_row else None

    def reset_track_titles_for_show(self, show_id: str, title_updates: List[Tuple[str, str]]) -> None:
        """Batch update episode titles for a show. title_updates is a list of (episode_id, new_title) tuples."""
        if not title_updates:
            return
        with self._get_connection() as conn:
            conn.executemany(
                "UPDATE episodes SET title = ?, is_custom_title = 0 WHERE show_id = ? AND episode_id = ?",
                [(new_title, show_id, ep_id) for ep_id, new_title in title_updates],
            )


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
        db_path: Path,
        cache_dir: Optional[Path] = None,
        max_episodes_per_show: int = 2000,
    ) -> None:
        self.books_dir = books_dir
        self.podcasts_dir = podcasts_dir
        self.cache_dir = cache_dir
        self.max_episodes_per_show = max_episodes_per_show
        self.cache = ScannerCache(db_path)

    def scan_folder(self, section: str, root_dir: Path, force: bool = False) -> List[Dict[str, Any]]:
        """Scan a top-level media directory (Books or Podcasts)."""
        start_time = time.perf_counter()
        logger.info(f"Scanning '{section}' media directory at {root_dir}")
        scanned_shows = []
        if not root_dir.exists() or not root_dir.is_dir():
            elapsed = time.perf_counter() - start_time
            logger.debug(f"Media directory {root_dir} does not exist or is not a directory")
            logger.info(f"Finished scanning '{section}' in {elapsed:.2f}s: indexed {len(scanned_shows)} shows")
            return scanned_shows

        for show_dir in sorted(root_dir.iterdir()):
            if not show_dir.is_dir() or show_dir.name.startswith("."):
                continue

            show_id = generate_show_id(section, show_dir.name)
            logger.debug(f"Indexing show directory '{show_dir.name}' (show_id={show_id})")

            # Determine cover image: check existing DB cache, then auto-locate
            cover_path = None
            if not force:
                cached_show = self.cache.get_show(show_id)
                if cached_show and cached_show.get("cover_path"):
                    cached_cover = Path(cached_show["cover_path"])
                    if cached_cover.is_file():
                        cover_path = cached_cover

            if not cover_path:
                cover_path = find_cover_image(show_dir)

            audio_files = []
            for item in show_dir.rglob("*"):
                if item.is_file() and item.suffix.lower() in AUDIO_EXTENSIONS:
                    audio_files.append(item)

            if not audio_files:
                logger.debug(f"No valid audio files found in {show_dir}, skipping")
                continue

            audio_files.sort(key=lambda item: episode_sort_key(item.relative_to(show_dir)))

            # Limit number of episodes per show based on max_episodes_per_show setting
            audio_files = audio_files[: self.max_episodes_per_show]

            # Fetch existing cached show metadata from SQLite to preserve custom cover BLOB & metadata across scans
            cached_show = self.cache.get_show(show_id, include_cover_data=True)
            display_title = (cached_show.get("title") if (cached_show and not force) else None) or show_dir.name

            # Fetch existing cached episode metadata for incremental scanning
            cached_episodes_map = {} if force else self.cache.get_episodes_map(show_id)

            episodes_info = []
            episodes_data = []
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
                else:
                    duration = get_audio_duration(audio_path)
                    bitrate_kbps = get_audio_bitrate(audio_path, file_size, duration)

                total_duration += duration
                total_file_size += file_size

                ep_id = f"{show_id}_ep_{idx}"
                rel_filename = str(audio_path.relative_to(show_dir))
                folder_parts = PurePath(rel_filename).parts[:-1]
                subfolder = "/".join(folder_parts) if folder_parts else ""
                track_name = get_audio_title(audio_path)
                stem = audio_path.stem

                episodes_info.append({
                    "tag_title": track_name,
                    "stem": stem,
                    "subfolder": subfolder,
                })

                episodes_data.append(
                    {
                        "episode_id": ep_id,
                        "filename": rel_filename,
                        "file_path": resolved_path_str,
                        "duration": duration,
                        "formatted_duration": format_duration(duration),
                        "file_size": file_size,
                        "formatted_file_size": format_file_size(file_size),
                        "bitrate": bitrate_kbps,
                        "formatted_bitrate": format_bitrate(bitrate_kbps),
                        "added_timestamp": mtime,
                        "cached_ep": cached_ep,
                    }
                )

            unique_titles = resolve_unique_track_titles(episodes_info)
            episodes = []
            for ep_data, unique_title in zip(episodes_data, unique_titles):
                cached_ep = ep_data.pop("cached_ep", None)
                if cached_ep and (cached_ep.get("is_custom_title") or (not force and cached_ep.get("title"))):
                    ep_data["title"] = cached_ep["title"]
                    ep_data["is_custom_title"] = cached_ep.get("is_custom_title", 0)
                else:
                    ep_data["title"] = unique_title
                    ep_data["is_custom_title"] = 0
                episodes.append(ep_data)

            if earliest_timestamp == float("inf"):
                earliest_timestamp = show_dir.stat().st_mtime

            # Fetch existing cached show metadata from SQLite to preserve custom cover BLOB & metadata across scans
            cached_show = self.cache.get_show(show_id, include_cover_data=True)
            cached_cover_data = cached_show.get("cover_data") if cached_show else None
            cached_cover_mime = cached_show.get("cover_mime", "") if cached_show else ""
            cached_cover_filename = cached_show.get("cover_filename", "") if cached_show else ""

            default_author = "Unknown Author" if section == "books" else ""
            default_publisher = "Podcast Publisher" if section == "podcasts" else ""

            display_title = (cached_show.get("title") if (cached_show and not force) else None) or show_dir.name
            author = (cached_show.get("author") if (cached_show and not force) else None) or (default_author if section == "books" else "")
            publisher = (cached_show.get("publisher") if (cached_show and not force) else None) or (default_publisher if section == "podcasts" else "")
            description = (cached_show.get("description") if (cached_show and not force) else None) or ""
            description_html = (cached_show.get("description_html") if (cached_show and not force) else None) or (markdown.markdown(description, extensions=["extra"]) if description else "")

            show_data = {
                "show_id": show_id,
                "section": section,
                "title": display_title,
                "author": author,
                "publisher": publisher,
                "podcast_name": display_title if section == "podcasts" else "",
                "folder_path": str(show_dir.resolve()),
                "cover_path": str(cover_path.resolve()) if cover_path else None,
                "cover_data": cached_cover_data,
                "cover_mime": cached_cover_mime,
                "cover_filename": cached_cover_filename,
                "total_duration": total_duration,
                "formatted_duration": format_duration(total_duration),
                "total_file_size": total_file_size,
                "formatted_total_file_size": format_file_size(total_file_size),
                "added_timestamp": earliest_timestamp,
                "fuzzy_added_date": format_fuzzy_date(earliest_timestamp),
                "description": description,
                "description_html": description_html,
                "notes_path": "",
            }

            self.cache.save_show(show_data, episodes)
            scanned_shows.append(show_data)

        elapsed = time.perf_counter() - start_time
        logger.info(f"Finished scanning '{section}' in {elapsed:.2f}s: indexed {len(scanned_shows)} shows")
        return scanned_shows

    def scan_all(self, force: bool = False) -> Dict[str, Any]:
        """Scan both Books and Podcasts sections, optionally forcing full metadata re-parse."""
        start_time = time.perf_counter()
        logger.info(f"Starting complete library scan (force={force})")
        books = self.scan_folder("books", self.books_dir, force=force)
        podcasts = self.scan_folder("podcasts", self.podcasts_dir, force=force)
        active_ids = [s["show_id"] for s in books + podcasts]
        self.cache.prune_deleted_shows(active_ids)
        total_count = len(books) + len(podcasts)
        elapsed = time.perf_counter() - start_time
        logger.info(
            f"Library scan complete in {elapsed:.2f}s: {len(books)} books, {len(podcasts)} podcasts ({total_count} total)"
        )
        return {"books": books, "podcasts": podcasts, "total": total_count}


    def update_show_metadata(
        self,
        show_id: str,
        title: str,
        author: str = "",
        description: str = "",
        publisher: str = "",
        cover: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Update title, author, publisher, description, and optional cover choice for a show in SQLite database."""
        show = self.cache.get_show(show_id, include_cover_data=True)
        if not show:
            return None

        section = show["section"]
        title = title.strip()
        description = description.strip()

        if section == "books":
            author = author.strip()
            publisher = ""
        else:
            publisher = publisher.strip() or author.strip()
            author = ""

        html_description = markdown.markdown(description, extensions=["extra"]) if description else ""

        if cover:
            show["cover_filename"] = cover
            show_dir = Path(show["folder_path"]).resolve()
            candidate_cover = show_dir / cover
            if candidate_cover.is_file():
                show["cover_path"] = str(candidate_cover.resolve())

        show["title"] = title
        show["author"] = author
        show["publisher"] = publisher
        if section == "podcasts":
            show["podcast_name"] = title
        show["description"] = description
        show["description_html"] = html_description

        self.cache.save_show(show, show["episodes"])
        return self.cache.get_show(show_id)

    def update_show_cover_data(
        self, show_id: str, cover_bytes: bytes, mime_type: str, filename: str, cover_path: Optional[Path] = None
    ) -> Optional[Dict[str, Any]]:
        """Update cover image binary BLOB in database cache and optional file path."""
        show = self.cache.get_show(show_id, include_cover_data=True)
        if not show:
            return None

        show["cover_data"] = cover_bytes
        show["cover_mime"] = mime_type
        show["cover_filename"] = filename
        if cover_path:
            show["cover_path"] = str(cover_path.resolve())

        self.cache.save_show(show, show["episodes"])
        return self.cache.get_show(show_id)

    def update_show_cover(self, show_id: str, new_cover_path: Path) -> Optional[Dict[str, Any]]:
        """Update cover_path and persist cover image binary BLOB in SQLite database."""
        show = self.cache.get_show(show_id, include_cover_data=True)
        if not show:
            return None

        resolved_cover = new_cover_path.resolve()
        if not resolved_cover.is_file():
            return None

        content = resolved_cover.read_bytes()
        ext = resolved_cover.suffix.lower()
        mime = "image/jpeg"
        if ext == ".png":
            mime = "image/png"
        elif ext == ".webp":
            mime = "image/webp"
        elif ext == ".svg":
            mime = "image/svg+xml"

        show_dir = Path(show["folder_path"]).resolve()
        try:
            rel_cover = str(resolved_cover.relative_to(show_dir))
        except ValueError:
            rel_cover = resolved_cover.name

        show["cover_path"] = str(resolved_cover)
        show["cover_data"] = content
        show["cover_mime"] = mime
        show["cover_filename"] = rel_cover

        self.cache.save_show(show, show["episodes"])

        return self.update_show_metadata(
            show_id=show_id,
            title=show["title"],
            author=show.get("author", ""),
            description=show.get("description", ""),
            publisher=show.get("publisher", ""),
            cover=rel_cover,
        )

    def update_episode_title(
        self, show_id: str, episode_id: str, new_title: str
    ) -> Optional[Dict[str, Any]]:
        """Update track/episode title in SQLite cache database."""
        return self.cache.update_episode_title(show_id, episode_id, new_title)

    def reset_show_track_titles(self, show_id: str) -> Optional[Dict[str, Any]]:
        """
        Reset all track titles for a show back to '<potential subfolder>/track title'
        where track title first tries media info tags or falls back to filename stem.
        If duplicates exist, falls back to filename stem for duplicate tracks.
        """
        show = self.cache.get_show(show_id)
        if not show:
            return None

        show_dir = Path(show["folder_path"])
        episodes_info = []
        ep_ids = []

        for ep in show.get("episodes", []):
            audio_path = Path(ep["file_path"])
            if not audio_path.is_file():
                audio_path = show_dir / ep["filename"]

            rel_filename = ep.get("filename", "")
            if audio_path.is_file():
                try:
                    rel_filename = str(audio_path.relative_to(show_dir))
                except ValueError:
                    pass
                tag_title = get_audio_title(audio_path)
                stem = audio_path.stem
            else:
                stem = Path(rel_filename).stem
                tag_title = stem

            folder_parts = PurePath(rel_filename).parts[:-1]
            subfolder = "/".join(folder_parts) if folder_parts else ""

            episodes_info.append({
                "tag_title": tag_title,
                "stem": stem,
                "subfolder": subfolder,
            })
            ep_ids.append(ep["episode_id"])

        unique_titles = resolve_unique_track_titles(episodes_info)
        title_updates = list(zip(ep_ids, unique_titles))

        if title_updates:
            self.cache.reset_track_titles_for_show(show_id, title_updates)

        return self.cache.get_show(show_id)


