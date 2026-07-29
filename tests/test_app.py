"""
Integration tests for FastAPI application endpoints in app.py.
"""

from typing import Generator
from fastapi.testclient import TestClient
import pytest

from lissn.app import app, scanner


@pytest.fixture
def client(temp_library) -> Generator[TestClient, None, None]:
    """Test client fixture configured with temporary library paths."""
    books_dir, podcasts_dir, cache_dir, cache_db = temp_library

    # Override scanner paths with temporary test library
    scanner.books_dir = books_dir
    scanner.podcasts_dir = podcasts_dir
    scanner.cache_dir = cache_dir
    scanner.cache.db_path = cache_db
    scanner.cache._init_db()
    scanner.scan_all()

    with TestClient(app) as test_client:
        yield test_client


def test_index_page(client: TestClient) -> None:
    """Test front page renders HTML with Books and Podcasts sections."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "lissn" in response.text
    assert "The Great Gatsby" in response.text
    assert "Tech Talk Podcast" in response.text
    assert 'data-section="all"' in response.text
    # Verify cover wrapper is a clickable link to show page
    assert 'class="cover-wrapper"' in response.text
    assert 'href="/show/' in response.text


def test_show_detail_page_with_opengraph_tags(client: TestClient) -> None:
    """Test show detail page renders with OpenGraph meta tags for social media sharing."""
    shows_res = client.get("/api/shows")
    shows = shows_res.json()["shows"]
    assert len(shows) > 0

    show_id = shows[0]["show_id"]
    response = client.get(f"/show/{show_id}")
    assert response.status_code == 200

    html = response.text
    assert '<meta property="og:title"' in html
    assert '<meta property="og:description"' in html
    assert '<meta name="twitter:card" content="summary_large_image"' in html
    assert f"/covers/{show_id}" in html
    assert 'class="detail-cover-link"' in html
    assert f'href="/covers/{show_id}"' in html
    assert "--show-color-1-rgb:" in html
    assert "--show-color-2-rgb:" in html
    assert "--show-color-3-rgb:" in html


def test_bottom_media_player_and_auto_continue(client: TestClient) -> None:
    """Test index and show detail pages render floating bottom media player with auto-continue controls."""
    # Test index page
    index_res = client.get("/")
    assert index_res.status_code == 200
    assert 'id="bottom-player"' in index_res.text
    assert 'id="auto-continue-btn"' in index_res.text
    assert "Auto-Next" in index_res.text

    # Test show detail page with track rows and play buttons
    shows_res = client.get("/api/shows")
    show_id = shows_res.json()["shows"][0]["show_id"]
    show_res = client.get(f"/show/{show_id}")
    assert show_res.status_code == 200

    html = show_res.text
    assert 'id="bottom-player"' in html
    assert 'id="auto-continue-btn"' in html
    assert 'class="track-row"' in html
    assert 'data-track-index="' in html
    assert 'data-audio-src="' in html
    assert 'js-play-track' in html
    assert '▶ Play' in html


def test_show_detail_page_not_found(client: TestClient) -> None:
    """Test show detail page returns HTTP 404 for invalid show ID."""
    response = client.get("/show/non_existent_show_id_999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Show not found"


def test_get_cover_image(client: TestClient) -> None:
    """Test cover image endpoint serves cover file."""
    shows_res = client.get("/api/shows")
    show_id = shows_res.json()["shows"][0]["show_id"]

    response = client.get(f"/covers/{show_id}")
    assert response.status_code == 200
    assert response.headers["content-type"] in ["image/jpeg", "image/png", "image/svg+xml"]


def test_get_cover_image_fallback_svg(client: TestClient) -> None:
    """Test cover image endpoint returns fallback SVG when show has no cover image or invalid ID."""
    response = client.get("/covers/non_existent_show_123")
    assert response.status_code == 200
    assert "image/svg+xml" in response.headers["content-type"]
    assert "<svg" in response.text
    assert "lissn" in response.text


def test_stream_audio_success(client: TestClient) -> None:
    """Test audio streaming endpoint returns audio file content."""
    shows_res = client.get("/api/shows")
    shows = shows_res.json()["shows"]
    book_info = next(s for s in shows if s["section"] == "books")

    show_id = book_info["show_id"]
    show_detail_res = client.get(f"/api/shows/{show_id}")
    show_detail = show_detail_res.json()
    filename = show_detail["episodes"][0]["filename"]

    response = client.get(f"/audio/{show_id}/{filename}")
    assert response.status_code == 200
    assert len(response.content) > 0


def test_stream_audio_not_found(client: TestClient) -> None:
    """Test audio streaming endpoint returns 404 for missing show or file."""
    shows_res = client.get("/api/shows")
    show_id = shows_res.json()["shows"][0]["show_id"]

    # Missing show
    res_bad_show = client.get("/audio/invalid_show_id/track.wav")
    assert res_bad_show.status_code == 404
    assert res_bad_show.json()["detail"] == "Show not found"

    # Missing file in valid show
    res_bad_file = client.get(f"/audio/{show_id}/non_existent_track.wav")
    assert res_bad_file.status_code == 404
    assert res_bad_file.json()["detail"] == "Audio file not found"


def test_stream_audio_directory_traversal_prevention(client: TestClient) -> None:
    """Test audio streaming endpoint blocks directory traversal attempts with HTTP 403 or 404."""
    shows_res = client.get("/api/shows")
    show_id = shows_res.json()["shows"][0]["show_id"]

    response = client.get(f"/audio/{show_id}/../../conftest.py")
    assert response.status_code in [403, 404]


def test_get_podcast_rss(client: TestClient) -> None:
    """Test RSS endpoint produces valid RSS XML response."""
    shows_res = client.get("/api/shows")
    show_id = shows_res.json()["shows"][0]["show_id"]

    response = client.get(f"/rss/{show_id}")
    assert response.status_code == 200
    assert "application/rss+xml" in response.headers["content-type"]
    assert "<rss " in response.text
    assert 'version="2.0"' in response.text
    assert "<enclosure" in response.text


def test_get_podcast_rss_not_found(client: TestClient) -> None:
    """Test RSS endpoint returns 404 when show is not found."""
    response = client.get("/rss/non_existent_show_id_999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Show not found"


def test_api_shows(client: TestClient) -> None:
    """Test REST API endpoint for shows."""
    response = client.get("/api/shows")
    assert response.status_code == 200
    data = response.json()
    assert "shows" in data
    assert data["count"] == 2


def test_api_shows_filtered_by_section(client: TestClient) -> None:
    """Test REST API endpoint filtered by section query parameter."""
    res_books = client.get("/api/shows?section=books")
    assert res_books.status_code == 200
    data_books = res_books.json()
    assert data_books["count"] == 1
    assert data_books["shows"][0]["section"] == "books"

    res_podcasts = client.get("/api/shows?section=podcasts")
    assert res_podcasts.status_code == 200
    data_podcasts = res_podcasts.json()
    assert data_podcasts["count"] == 1
    assert data_podcasts["shows"][0]["section"] == "podcasts"


def test_api_get_show_detail(client: TestClient) -> None:
    """Test REST API endpoint for single show detail."""
    shows_res = client.get("/api/shows")
    show_id = shows_res.json()["shows"][0]["show_id"]

    response = client.get(f"/api/shows/{show_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["show_id"] == show_id
    assert "title" in data
    assert "episodes" in data


def test_api_get_show_detail_not_found(client: TestClient) -> None:
    """Test REST API endpoint for single show detail returns 404 when not found."""
    response = client.get("/api/shows/invalid_show_id_999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Show not found"


def test_api_rescan(client: TestClient) -> None:
    """Test REST API endpoint for library rescan."""
    response = client.post("/api/scan")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"


def test_partial_http_range_requests(client: TestClient) -> None:
    """Test partial HTTP Range requests return status 206 Partial Content and Content-Range header."""
    shows_res = client.get("/api/shows")
    shows = shows_res.json()["shows"]
    book_info = next(s for s in shows if s["section"] == "books")
    show_id = book_info["show_id"]
    show_detail = client.get(f"/api/shows/{show_id}").json()
    filename = show_detail["episodes"][0]["filename"]

    # Request first 10 bytes
    response = client.get(f"/audio/{show_id}/{filename}", headers={"Range": "bytes=0-9"})
    assert response.status_code == 206
    assert response.headers["accept-ranges"] == "bytes"
    assert "content-range" in response.headers
    assert response.headers["content-range"].startswith("bytes 0-9/")
    assert len(response.content) == 10

    # Request tail range
    res_tail = client.get(f"/audio/{show_id}/{filename}", headers={"Range": "bytes=-5"})
    assert res_tail.status_code == 206
    assert len(res_tail.content) == 5


def test_unsatisfiable_http_range_request(client: TestClient) -> None:
    """Test invalid HTTP Range request returns 416 Range Not Satisfiable."""
    shows_res = client.get("/api/shows")
    show_id = shows_res.json()["shows"][0]["show_id"]
    show_detail = client.get(f"/api/shows/{show_id}").json()
    filename = show_detail["episodes"][0]["filename"]

    response = client.get(f"/audio/{show_id}/{filename}", headers={"Range": "bytes=9999999-99999999"})
    assert response.status_code == 416
    assert "content-range" in response.headers


def test_head_requests(client: TestClient) -> None:
    """Test HTTP HEAD method requests return metadata headers with empty body."""
    shows_res = client.get("/api/shows")
    show_id = shows_res.json()["shows"][0]["show_id"]
    show_detail = client.get(f"/api/shows/{show_id}").json()
    filename = show_detail["episodes"][0]["filename"]

    # HEAD audio stream
    res_audio = client.head(f"/audio/{show_id}/{filename}")
    assert res_audio.status_code == 200
    assert res_audio.headers["accept-ranges"] == "bytes"
    assert "content-length" in res_audio.headers
    assert len(res_audio.content) == 0

    # HEAD index page
    res_index = client.head("/")
    assert res_index.status_code == 200
    assert len(res_index.content) == 0


def test_security_and_protocol_headers(client: TestClient) -> None:
    """Test response middleware injects modern web security headers."""
    response = client.get("/")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "SAMEORIGIN"
    assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert "permissions-policy" in response.headers


def test_audiobook_m4b_m4a_mime_types(client: TestClient) -> None:
    """Test custom audio MIME types for .m4b and .m4a audiobooks."""
    import mimetypes
    assert mimetypes.guess_type("audiobook.m4b")[0] == "audio/mp4"
    assert mimetypes.guess_type("podcast.m4a")[0] == "audio/mp4"


def test_client_navigation_and_accessibility_announcer(client: TestClient) -> None:
    """Test index and show detail pages contain aria-announcer for screen reader feedback."""
    index_res = client.get("/")
    assert index_res.status_code == 200
    assert 'id="aria-announcer"' in index_res.text
    assert 'class="sr-only"' in index_res.text
    assert 'aria-live="polite"' in index_res.text

    shows_res = client.get("/api/shows")
    show_id = shows_res.json()["shows"][0]["show_id"]
    show_res = client.get(f"/show/{show_id}")
    assert show_res.status_code == 200
    assert 'id="aria-announcer"' in show_res.text
    assert 'class="sr-only"' in show_res.text


