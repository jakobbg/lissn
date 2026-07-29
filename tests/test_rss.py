"""
Unit tests for rss.py Podcast RSS generator module.
"""

from xml.etree import ElementTree as ET

from lissn.rss import generate_rss_feed, get_mime_type


def test_get_mime_type() -> None:
    """Test MIME type resolution for audio file extensions."""
    assert get_mime_type("audio.mp3") == "audio/mpeg"
    assert get_mime_type("track.m4a") == "audio/mp4"
    assert get_mime_type("book.m4b") == "audio/x-m4b"
    assert get_mime_type("recording.wav") == "audio/wav"
    assert get_mime_type("unknown.xyz") == "audio/mpeg"


def test_generate_rss_feed() -> None:
    """Test generating RSS 2.0 Podcast XML feed."""
    show_data = {
        "show_id": "test_show_123",
        "section": "podcasts",
        "title": "Daily Tech Podcast",
        "description": "Daily insights into software and AI.",
        "cover_path": "/path/to/cover.jpg",
        "episodes": [
            {
                "episode_id": "test_show_123_ep_1",
                "title": "Episode 1: Launch Day",
                "filename": "ep1.mp3",
                "file_size": 10485760,
                "duration": 600.0,
                "added_timestamp": 1700000000.0,
            }
        ],
    }

    xml_output = generate_rss_feed(show_data=show_data, base_url="http://localhost:8000")

    assert xml_output.startswith('<?xml version="1.0" encoding="UTF-8"?>')

    root = ET.fromstring(xml_output.split("\n", 1)[1])
    assert root.tag == "rss"
    assert root.attrib.get("version") == "2.0"

    channel = root.find("channel")
    assert channel is not None
    assert channel.find("title").text == "Daily Tech Podcast"
    assert channel.find("link").text == "http://localhost:8000/show/test_show_123"

    items = channel.findall("item")
    assert len(items) == 1

    item = items[0]
    assert item.find("title").text == "Episode 1: Launch Day"

    enclosure = item.find("enclosure")
    assert enclosure is not None
    assert enclosure.attrib["url"] == "http://localhost:8000/audio/test_show_123/ep1.mp3"
    assert enclosure.attrib["type"] == "audio/mpeg"
    assert enclosure.attrib["length"] == "10485760"
