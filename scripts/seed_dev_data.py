"""
Dev Data Seeder for lissn.
Generates local sample Audio Books and Podcasts with valid dummy audio files, cover images,
and metadata notes.md files in ./data/Books and ./data/Podcasts.
Allows running and debugging lissn locally without needing external media files.
"""

from pathlib import Path
import struct
import wave
from typing import Tuple
from PIL import Image, ImageDraw, ImageFont


def create_dummy_wav(path: Path, duration_seconds: float = 3.0) -> None:
    """
    Generate a minimal valid silent WAV audio file.

    Args:
        path: Target file path to write the WAV audio.
        duration_seconds: Duration of silent audio in seconds.
    """
    sample_rate = 8000
    n_samples = int(sample_rate * duration_seconds)

    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        data = struct.pack(f"<{n_samples}h", *([0] * n_samples))
        wav_file.writeframes(data)


def create_sample_cover(path: Path, title: str, bg_color: Tuple[int, int, int]) -> None:
    """
    Generate a simple sample cover image with title text.

    Args:
        path: Target image file path.
        title: Title string to draw on the cover.
        bg_color: RGB tuple for the cover background color.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (600, 600), color=bg_color)
    draw = ImageDraw.Draw(img)

    # Draw decorative rectangle
    draw.rectangle([40, 40, 560, 560], outline=(255, 255, 255), width=4)

    # Simple text placement
    draw.text((300, 280), title, fill=(255, 255, 255), anchor="mm")
    img.save(path)


def seed_local_data() -> None:
    """Populate local ./data/Books and ./data/Podcasts with sample media."""
    base_dir = Path.cwd()
    books_dir = base_dir / "data" / "Books"
    podcasts_dir = base_dir / "data" / "Podcasts"

    print("🌱 Seeding local development media library...")

    # 1. Sample Audiobook: The Great Gatsby
    gatsby_dir = books_dir / "The Great Gatsby"
    create_sample_cover(gatsby_dir / "cover.jpg", "The Great Gatsby", (30, 41, 59))
    create_dummy_wav(gatsby_dir / "01_chapter1.wav", duration_seconds=15.0)
    create_dummy_wav(gatsby_dir / "02_chapter2.wav", duration_seconds=25.0)
    (gatsby_dir / "notes.md").write_text(
        "---\n"
        "title: The Great Gatsby\n"
        "author: F. Scott Fitzgerald\n"
        "---\n"
        "The story of the mysteriously wealthy Jay Gatsby and his passion for Daisy Buchanan.\n",
        encoding="utf-8",
    )

    # 2. Sample Audiobook: 1984
    orwell_dir = books_dir / "1984"
    create_sample_cover(orwell_dir / "cover.png", "1984", (127, 29, 29))
    create_dummy_wav(orwell_dir / "01_part1.wav", duration_seconds=30.0)
    create_dummy_wav(orwell_dir / "02_part2.wav", duration_seconds=45.0)

    # 3. Sample Podcast: Tech Talk Podcast
    techtalk_dir = podcasts_dir / "Tech Talk Podcast"
    create_sample_cover(techtalk_dir / "poster.png", "Tech Talk", (79, 70, 229))
    create_dummy_wav(techtalk_dir / "ep1_ai_future.wav", duration_seconds=18.0)
    create_dummy_wav(techtalk_dir / "ep2_web_dev.wav", duration_seconds=22.0)
    (techtalk_dir / "notes.md").write_text(
        "---\n"
        "podcast_name: Tech Talk Podcast\n"
        "author: Dev Team\n"
        "---\n"
        "A weekly discussion on modern web development, artificial intelligence, and open source software.\n",
        encoding="utf-8",
    )

    # 4. Sample Podcast: Daily News
    news_dir = podcasts_dir / "Daily News"
    create_sample_cover(news_dir / "cover.jpg", "Daily News", (6, 95, 70))
    create_dummy_wav(news_dir / "2026-07-29_update.wav", duration_seconds=10.0)

    print("✅ Sample media library seeded successfully in ./data/Books and ./data/Podcasts!")


if __name__ == "__main__":
    seed_local_data()
