"""
Unit tests for rss.py Podcast RSS generator module.
"""

from xml.etree import ElementTree as ET

from lissn.rss import generate_rss_feed, get_mime_type


def test_get_mime_type() -> None:
    """Test MIME type resolution for audio file extensions."""
    assert get_mime_type("audio.mp3") == "audio/mpeg"
    assert get_mime_type("track.m4a") == "audio/mp4"
    assert get_mime_type("book.m4b") == "audio/mp4"
    assert get_mime_type("recording.wav") == "audio/wav"
    assert get_mime_type("unknown.xyz") == "audio/mpeg"


def test_generate_rss_feed() -> None:
    """Test generating RSS 2.0 Podcast XML feed without author."""
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


def test_generate_rss_feed_with_author_podcast_and_book() -> None:
    """Test that publisher/author is appended in parenthesis after title for podcasts and audiobooks."""
    # Test Podcast section with publisher
    podcast_data = {
        "show_id": "pod_1",
        "section": "podcasts",
        "title": "Tech Talk",
        "publisher": "Tech Media Corp",
        "description": "Podcast about tech.",
        "episodes": [],
    }
    xml_podcast = generate_rss_feed(show_data=podcast_data, base_url="http://localhost:8000")
    root_pod = ET.fromstring(xml_podcast.split("\n", 1)[1])
    chan_pod = root_pod.find("channel")
    assert chan_pod.find("title").text == "Tech Talk (Tech Media Corp)"
    itunes_author_pod = chan_pod.find("{http://www.itunes.com/dtds/podcast-1.0.dtd}author")
    assert itunes_author_pod is not None
    assert itunes_author_pod.text == "Tech Media Corp"

    # Test Audiobook (books section) with author/publisher
    book_data = {
        "show_id": "book_1",
        "section": "books",
        "title": "The Great Gatsby",
        "author": "F. Scott Fitzgerald",
        "description": "Classic novel.",
        "episodes": [],
    }
    xml_book = generate_rss_feed(show_data=book_data, base_url="http://localhost:8000")
    root_book = ET.fromstring(xml_book.split("\n", 1)[1])
    chan_book = root_book.find("channel")
    assert chan_book.find("title").text == "The Great Gatsby (F. Scott Fitzgerald)"
    itunes_author_book = chan_book.find("{http://www.itunes.com/dtds/podcast-1.0.dtd}author")
    assert itunes_author_book is not None
    assert itunes_author_book.text == "F. Scott Fitzgerald"

