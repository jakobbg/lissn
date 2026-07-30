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

from lissn.version import get_app_metadata


MIME_TYPES = {
    ".mp3": "audio/mpeg",
    ".m4a": "audio/mp4",
    ".m4b": "audio/mp4",
    ".aac": "audio/aac",
    ".flac": "audio/flac",
    ".ogg": "audio/ogg",
    ".opus": "audio/opus",
    ".wav": "audio/wav",
}


ET.register_namespace("itunes", "http://www.itunes.com/dtds/podcast-1.0.dtd")
ET.register_namespace("content", "http://purl.org/rss/1.0/modules/content/")
ET.register_namespace("podcast", "https://podcastindex.org/podcast-1.0")
ET.register_namespace("atom", "http://www.w3.org/2005/Atom")


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
    app_meta = get_app_metadata()
    show_id = show_data["show_id"]
    raw_title = show_data["title"]
    section = show_data.get("section", "podcasts")
    if section == "podcasts":
        creator = (show_data.get("publisher") or show_data.get("author") or "").strip()
    else:
        creator = (show_data.get("author") or "").strip()

    if creator:
        title = f"{raw_title} ({creator})"
    else:
        title = raw_title

    base_desc = show_data.get("description") or f"{raw_title} ({section.capitalize()})"
    served_by_suffix = app_meta["served_by_info"]
    description = f"{base_desc}\n\n{served_by_suffix}"

    clean_base = base_url.rstrip("/")

    feed_url = f"{clean_base}/rss/{show_id}"
    show_page_url = f"{clean_base}/show/{show_id}"

    if show_data.get("cover_path"):
        ext = Path(show_data["cover_path"]).suffix.lower()
        if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
            ext = ".jpg"
        cover_url = f"{clean_base}/covers/{show_id}{ext}"
    else:
        cover_url = ""

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
    ET.SubElement(channel, "generator").text = f"lissn v{app_meta['app_version']} (commit {app_meta['git_commit']})"

    # Self Atom link for PSP-1 & RSS standard compliance
    ET.SubElement(
        channel,
        "{http://www.w3.org/2005/Atom}link",
        {
            "href": feed_url,
            "rel": "self",
            "type": "application/rss+xml",
        },
    )

    # iTunes podcast category & explicit rating
    category = (show_data.get("category") or "Technology").strip()
    ET.SubElement(
        channel,
        "{http://www.itunes.com/dtds/podcast-1.0.dtd}category",
        {"text": category},
    )

    is_explicit = "true" if show_data.get("explicit") else "false"
    ET.SubElement(
        channel,
        "{http://www.itunes.com/dtds/podcast-1.0.dtd}explicit",
    ).text = is_explicit

    if creator:
        ET.SubElement(channel, "{http://www.itunes.com/dtds/podcast-1.0.dtd}author").text = creator

    itunes_summary = ET.SubElement(channel, "{http://www.itunes.com/dtds/podcast-1.0.dtd}summary")
    itunes_summary.text = description

    if cover_url:
        image_elem = ET.SubElement(channel, "image")
        ET.SubElement(image_elem, "url").text = cover_url
        ET.SubElement(image_elem, "title").text = title
        ET.SubElement(image_elem, "link").text = show_page_url

        ET.SubElement(
            channel,
            "{http://www.itunes.com/dtds/podcast-1.0.dtd}image",
            {"href": cover_url},
        )

    episodes = show_data.get("episodes", [])
    for ep in episodes:
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = ep["title"]

        ep_link = f"{show_page_url}#ep-{ep['episode_id']}"
        ET.SubElement(item, "link").text = ep_link

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

        ET.SubElement(
            item,
            "{http://www.itunes.com/dtds/podcast-1.0.dtd}explicit",
        ).text = is_explicit

        if ep.get("duration"):
            dur_seconds = int(ep["duration"])
            itunes_dur = ET.SubElement(
                item, "{http://www.itunes.com/dtds/podcast-1.0.dtd}duration"
            )
            itunes_dur.text = str(dur_seconds)

    xml_declaration = '<?xml version="1.0" encoding="UTF-8"?>\n'
    return xml_declaration + ET.tostring(rss, encoding="utf-8").decode("utf-8")

