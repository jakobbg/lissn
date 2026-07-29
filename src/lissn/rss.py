"""
RSS 2.0 feed generator for lissn shows.
Produces valid Podcast RSS 2.0 XML feeds with iTunes tags for podcast player subscription.
"""

from datetime import datetime, timezone
import email.utils
from pathlib import Path
from typing import Any, Dict
from urllib.parse import quote
from xml.etree import ElementTree as ET


MIME_TYPES = {
    ".mp3": "audio/mpeg",
    ".m4a": "audio/mp4",
    ".m4b": "audio/x-m4b",
    ".aac": "audio/aac",
    ".flac": "audio/flac",
    ".ogg": "audio/ogg",
    ".opus": "audio/opus",
    ".wav": "audio/wav",
}


ET.register_namespace("itunes", "http://www.itunes.com/dtds/podcast-1.0.dtd")
ET.register_namespace("content", "http://purl.org/rss/1.0/modules/content/")


def get_mime_type(filename: str) -> str:
    """Return appropriate audio MIME type for an audio filename."""
    ext = Path(filename).suffix.lower()
    return MIME_TYPES.get(ext, "audio/mpeg")


def format_rfc822(timestamp: float) -> str:
    """Format a POSIX timestamp into an RFC 822 date string for RSS."""
    dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    return email.utils.format_datetime(dt)


def generate_rss_feed(show_data: Dict[str, Any], base_url: str) -> str:
    """
    Generate RSS 2.0 XML string for a show.

    Args:
        show_data: Dictionary containing show metadata and list of episodes.
        base_url: Absolute HTTP base URL of the lissn server.

    Returns:
        XML string representing the podcast RSS feed.
    """
    show_id = show_data["show_id"]
    raw_title = show_data["title"]
    author = (show_data.get("author") or "").strip()
    if author:
        title = f"{raw_title} ({author})"
    else:
        title = raw_title

    description = show_data.get("description") or f"{raw_title} ({show_data['section'].capitalize()})"
    clean_base = base_url.rstrip("/")

    feed_url = f"{clean_base}/rss/{show_id}"
    show_page_url = f"{clean_base}/show/{show_id}"
    cover_url = f"{clean_base}/covers/{show_id}" if show_data.get("cover_path") else ""

    rss = ET.Element(
        "rss",
        {
            "version": "2.0",
        },
    )

    channel = ET.SubElement(rss, "channel")

    ET.SubElement(channel, "title").text = title
    ET.SubElement(channel, "link").text = show_page_url
    ET.SubElement(channel, "description").text = description
    ET.SubElement(channel, "language").text = "en-us"
    ET.SubElement(channel, "generator").text = "lissn v0.1"

    if author:
        ET.SubElement(channel, "{http://www.itunes.com/dtds/podcast-1.0.dtd}author").text = author

    itunes_summary = ET.SubElement(channel, "{http://www.itunes.com/dtds/podcast-1.0.dtd}summary")
    itunes_summary.text = description

    if cover_url:
        image_elem = ET.SubElement(channel, "image")
        ET.SubElement(image_elem, "url").text = cover_url
        ET.SubElement(image_elem, "title").text = title
        ET.SubElement(image_elem, "link").text = show_page_url

        itunes_image = ET.SubElement(
            channel,
            "{http://www.itunes.com/dtds/podcast-1.0.dtd}image",
            {"href": cover_url},
        )

    episodes = show_data.get("episodes", [])
    for ep in episodes:
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = ep["title"]
        ET.SubElement(item, "guid", {"isPermaLink": "false"}).text = ep["episode_id"]

        pub_date = format_rfc822(ep["added_timestamp"])
        ET.SubElement(item, "pubDate").text = pub_date

        audio_url = f"{clean_base}/audio/{show_id}/{quote(ep['filename'], safe='/')}"
        mime_type = get_mime_type(ep["filename"])

        ET.SubElement(
            item,
            "enclosure",
            {
                "url": audio_url,
                "length": str(ep["file_size"]),
                "type": mime_type,
            },
        )

        if ep.get("duration"):
            dur_seconds = int(ep["duration"])
            itunes_dur = ET.SubElement(
                item, "{http://www.itunes.com/dtds/podcast-1.0.dtd}duration"
            )
            itunes_dur.text = str(dur_seconds)

    xml_declaration = '<?xml version="1.0" encoding="UTF-8"?>\n'
    return xml_declaration + ET.tostring(rss, encoding="utf-8").decode("utf-8")
