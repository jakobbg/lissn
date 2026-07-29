"""
Pytest configuration and shared test fixtures for lissn.
Creates temporary sample Books and Podcasts directory structures with valid audio files and cover art.
"""

from pathlib import Path
import struct
import tempfile
import wave
from typing import Generator, Tuple

import pytest


def create_dummy_wav(path: Path, duration_seconds: float = 1.0) -> None:
    """Create a minimal valid WAV audio file with specified duration."""
    sample_rate = 8000
    n_samples = int(sample_rate * duration_seconds)
    
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        
        # Write silent PCM audio data
        data = struct.pack(f"<{n_samples}h", *([0] * n_samples))
        wav_file.writeframes(data)


@pytest.fixture
def temp_library() -> Generator[Tuple[Path, Path, Path, Path], None, None]:
    """
    Fixture providing temporary Books, Podcasts, Cache directory, and Cache DB paths with mock show folders.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        books_dir = tmp_path / "Books"
        podcasts_dir = tmp_path / "Podcasts"
        cache_dir = tmp_path / "cache"
        cache_db = cache_dir / "lissn_cache.db"

        books_dir.mkdir(parents=True, exist_ok=True)
        podcasts_dir.mkdir(parents=True, exist_ok=True)
        cache_dir.mkdir(parents=True, exist_ok=True)

        # 1. Create a sample Audiobook show: "The Great Gatsby"
        book_show = books_dir / "The Great Gatsby"
        book_show.mkdir()

        # Cover image
        (book_show / "cover.jpg").write_bytes(
            b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00"
        )
        # Audio tracks
        create_dummy_wav(book_show / "01_chapter1.wav", duration_seconds=5.0)
        create_dummy_wav(book_show / "02_chapter2.wav", duration_seconds=10.0)
        create_dummy_wav(book_show / "Bare en drøm#.wav", duration_seconds=3.0)

        # 2. Create a sample Podcast show: "Tech Talk Podcast"
        podcast_show = podcasts_dir / "Tech Talk Podcast"
        podcast_show.mkdir()

        # Cover image
        (podcast_show / "poster.png").write_bytes(
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        )
        # Audio tracks
        create_dummy_wav(podcast_show / "ep1_ai_future.wav", duration_seconds=12.0)

        yield books_dir, podcasts_dir, cache_dir, cache_db
