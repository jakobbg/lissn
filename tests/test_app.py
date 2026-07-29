"""
Integration tests for FastAPI application endpoints in app.py.
"""

from typing import Generator
from fastapi.testclient import TestClient
import pytest

from lissn.app import app, config, scanner


@pytest.fixture
def client(temp_library) -> Generator[TestClient, None, None]:
    """Test client fixture configured with temporary library paths and authenticated session."""
    books_dir, podcasts_dir, cache_dir, cache_db = temp_library

    # Override scanner paths with temporary test library
    scanner.books_dir = books_dir
    scanner.podcasts_dir = podcasts_dir
    scanner.cache_dir = cache_dir
    scanner.cache.db_path = cache_db
    scanner.cache._init_db()
    scanner.scan_all()

    with TestClient(app) as test_client:
        test_client.post("/api/login", json={"password": config.password})
        yield test_client


@pytest.fixture
def unauthenticated_client(temp_library) -> Generator[TestClient, None, None]:
    """Test client fixture configured without session authentication."""
    books_dir, podcasts_dir, cache_dir, cache_db = temp_library

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
    assert 'id="show-' in response.text
    assert 'tabindex="-1"' in response.text


def test_back_to_library_anchor_and_show_card_ids(client: TestClient) -> None:
    """Test Back to Library button anchors to the specific show card ID for scroll positioning."""
    shows_res = client.get("/api/shows")
    shows = shows_res.json()["shows"]
    assert len(shows) > 0

    show_id = shows[0]["show_id"]
    response = client.get(f"/show/{show_id}")
    assert response.status_code == 200

    html = response.text
    assert f'href="/#show-{show_id}"' in html
    assert "← Back to Library" in html


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
    assert 'class="detail-cover-link' in html
    assert 'js-zoom-cover' in html
    assert f'data-cover-url="/covers/{show_id}"' in html
    assert f'href="/covers/{show_id}"' not in html
    assert "--show-color-1-rgb:" in html
    assert "--show-color-2-rgb:" in html
    assert "--show-color-3-rgb:" in html


def test_show_cover_zoom_modal_markup(client: TestClient) -> None:
    """Test show detail page renders cover image zoom modal and button triggering zoom instead of direct file link."""
    shows_res = client.get("/api/shows")
    shows = shows_res.json()["shows"]
    assert len(shows) > 0

    show_id = shows[0]["show_id"]
    response = client.get(f"/show/{show_id}")
    assert response.status_code == 200

    html = response.text
    # Verify cover image element does not directly link to file via href
    assert f'href="/covers/{show_id}"' not in html
    # Verify zoom modal markup and button trigger data attributes exist
    assert 'id="cover-modal"' in html
    assert 'id="cover-modal-image"' in html
    assert 'class="modal-close-btn cover-modal-close js-close-cover-modal"' in html
    assert 'js-zoom-cover' in html
    assert f'data-cover-url="/covers/{show_id}"' in html


def test_bottom_media_player_and_auto_continue(client: TestClient) -> None:
    """Test index and show detail pages render floating bottom media player with auto-continue controls."""
    # Test index page
    index_res = client.get("/")
    assert index_res.status_code == 200
    assert 'id="bottom-player"' in index_res.text
    assert 'id="auto-continue-btn"' in index_res.text
    assert 'id="player-close-btn"' in index_res.text
    assert "Close audio player" in index_res.text
    assert "Auto-Next" in index_res.text

    # Test show detail page with track rows and play buttons
    shows_res = client.get("/api/shows")
    show_id = shows_res.json()["shows"][0]["show_id"]
    show_res = client.get(f"/show/{show_id}")
    assert show_res.status_code == 200

    html = show_res.text
    assert 'id="bottom-player"' in html
    assert 'id="auto-continue-btn"' in html
    assert 'id="player-close-btn"' in html
    assert 'class="track-row"' in html
    assert 'data-track-index="' in html
    assert 'data-audio-src="' in html
    assert 'js-play-track' in html
    assert 'btn-play-icon' in html
    assert 'player-icon' in html


def test_sleep_timer_and_duration_remaining_toggle(client: TestClient) -> None:
    """Test sleep timer control with 5, 10, 15, 30, 45 mins, 1h options and duration remaining toggle display."""
    response = client.get("/")
    assert response.status_code == 200
    html = response.text

    # Check Sleep Timer HTML components
    assert 'id="sleep-timer-btn"' in html
    assert 'id="sleep-timer-select"' in html
    assert 'id="sleep-timer-badge"' in html
    assert '<option value="5">5 mins</option>' in html
    assert '<option value="10">10 mins</option>' in html
    assert '<option value="15">15 mins</option>' in html
    assert '<option value="30">30 mins</option>' in html
    assert '<option value="45">45 mins</option>' in html
    assert '<option value="60">1 hour</option>' in html

    # Check Total Time toggleable duration element
    assert 'id="player-total-time"' in html
    assert 'player-time-toggleable' in html
    assert 'title="Click to toggle remaining time"' in html

    # Check edit-modal structure is rendered on index page as well
    assert 'id="edit-modal"' in html

    # Verify sr-only CSS class exists in style.css so screen reader announcements are visually hidden
    css_res = client.get("/static/style.css")
    assert css_res.status_code == 200
    assert ".sr-only" in css_res.text
    assert "position: absolute;" in css_res.text
    assert "clip: rect(0, 0, 0, 0);" in css_res.text


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


def test_stream_audio_special_characters(client: TestClient) -> None:
    """Test audio streaming and downloading for filenames with special characters like '#' and 'drøm'."""
    shows_res = client.get("/api/shows")
    shows = shows_res.json()["shows"]
    book_info = next(s for s in shows if s["section"] == "books")
    show_id = book_info["show_id"]

    # Verify HTML template encodes special characters in data-audio-src and href attributes
    html_res = client.get(f"/show/{show_id}")
    assert html_res.status_code == 200
    assert "Bare%20en%20dr%C3%B8m%23.wav" in html_res.text or "Bare%20en%20dr" in html_res.text

    # Stream audio with percent-encoded '#' (%23)
    res_audio = client.get(f"/audio/{show_id}/Bare%20en%20dr%C3%B8m%23.wav")
    assert res_audio.status_code == 200
    assert len(res_audio.content) > 0

    # Download episode with percent-encoded '#' (%23)
    res_dl = client.get(f"/download/{show_id}/Bare%20en%20dr%C3%B8m%23.wav")
    assert res_dl.status_code == 200
    assert len(res_dl.content) > 0


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


def test_single_episode_download_endpoint(client: TestClient) -> None:
    """Test downloading a single episode audio file via /download/{show_id}/{filename}."""
    shows_res = client.get("/api/shows")
    show_id = shows_res.json()["shows"][0]["show_id"]
    show_detail = client.get(f"/api/shows/{show_id}").json()
    filename = show_detail["episodes"][0]["filename"]

    response = client.get(f"/download/{show_id}/{filename}")
    assert response.status_code == 200
    assert "attachment" in response.headers.get("content-disposition", "")
    assert filename in response.headers.get("content-disposition", "")


def test_show_zip_download_endpoint(client: TestClient) -> None:
    """Test downloading complete show audio files bundled as a ZIP archive via /download/show/{show_id}."""
    import io
    import zipfile

    shows_res = client.get("/api/shows")
    show_id = shows_res.json()["shows"][0]["show_id"]

    response = client.get(f"/download/show/{show_id}")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert "attachment" in response.headers.get("content-disposition", "")

    # Verify ZIP contents
    zip_buf = io.BytesIO(response.content)
    with zipfile.ZipFile(zip_buf, "r") as zf:
        namelist = zf.namelist()
        assert len(namelist) > 0


def test_show_page_displays_filesize_and_bitrate(client: TestClient) -> None:
    """Test show detail page renders total filesize, episode filesize, bitrate, and download buttons."""
    shows_res = client.get("/api/shows")
    show_id = shows_res.json()["shows"][0]["show_id"]
    response = client.get(f"/show/{show_id}")
    assert response.status_code == 200

    html = response.text
    assert "Total Size" in html
    assert "Size" in html
    assert "Bitrate" in html
    assert "Download Show (.zip)" in html
    assert "js-download-track" in html
    assert f"/download/show/{show_id}" in html
    assert f"/download/{show_id}/" in html


def test_compact_track_layout(client: TestClient) -> None:
    """Test compact track layout has play button on the left before track #, title tooltip, and download on the right."""
    shows_res = client.get("/api/shows")
    show_id = shows_res.json()["shows"][0]["show_id"]
    response = client.get(f"/show/{show_id}")
    assert response.status_code == 200

    html = response.text
    assert 'class="track-table"' in html
    assert 'class="track-row"' in html
    assert 'track-title-text' in html
    # Check play button appears before track index inside row
    play_idx = html.find('js-play-track')
    dl_idx = html.find('js-download-track')
    assert play_idx != -1
    assert dl_idx != -1
    assert play_idx < dl_idx
    # Check title hover attribute
    assert 'title="File: ' in html


def test_login_success_and_failure(unauthenticated_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test /api/login endpoint returns 200 and sets session cookie for valid password, and 401 with error message for invalid password."""
    from lissn.app import config

    client = unauthenticated_client
    monkeypatch.setattr(config, "password", "mysecretpass")

    # Test incorrect password
    res_bad = client.post("/api/login", json={"password": "wrongpassword"})
    assert res_bad.status_code == 401
    assert res_bad.json()["detail"] == "Sorry, the password is incorrect"

    # Test correct password
    res_ok = client.post("/api/login", json={"password": "mysecretpass"})
    assert res_ok.status_code == 200
    data = res_ok.json()
    assert data["status"] == "success"
    assert data["authenticated"] is True
    assert "lissn_session" in res_ok.cookies


def test_protected_endpoints_require_auth(unauthenticated_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that play, download, and edit endpoints return 401 when unauthenticated and 200 when logged in."""
    from lissn.app import config

    client = unauthenticated_client
    monkeypatch.setattr(config, "password", "testpass")

    shows_res = client.get("/api/shows")
    show = shows_res.json()["shows"][0]
    show_id = show["show_id"]

    show_detail = client.get(f"/api/shows/{show_id}").json()
    ep = show_detail["episodes"][0]
    filename = ep["filename"]

    # 1. Accessing audio stream without auth
    res_audio = client.get(f"/audio/{show_id}/{filename}")
    assert res_audio.status_code == 401

    # 2. Accessing download show zip without auth
    res_zip = client.get(f"/download/show/{show_id}")
    assert res_zip.status_code == 401

    # 3. Accessing download episode without auth
    res_ep = client.get(f"/download/{show_id}/{filename}")
    assert res_ep.status_code == 401

    # 4. Accessing edit show endpoint without auth
    res_edit = client.post(
        f"/api/shows/{show_id}/edit",
        json={"title": "New Title", "author": "New Author", "description": "New Desc"},
    )
    assert res_edit.status_code == 401

    # Now login successfully
    login_res = client.post("/api/login", json={"password": "testpass"})
    assert login_res.status_code == 200

    # Repeat requests with authenticated session client
    res_audio_auth = client.get(f"/audio/{show_id}/{filename}")
    assert res_audio_auth.status_code in (200, 206)

    res_zip_auth = client.get(f"/download/show/{show_id}")
    assert res_zip_auth.status_code == 200

    res_ep_auth = client.get(f"/download/{show_id}/{filename}")
    assert res_ep_auth.status_code == 200

    res_edit_auth = client.post(
        f"/api/shows/{show_id}/edit",
        json={"title": "Updated Title", "author": "Updated Author", "description": "**Bold** notes"},
    )
    assert res_edit_auth.status_code == 200
    assert res_edit_auth.json()["show"]["title"] == "Updated Title"


def test_edit_show_markdown_and_notes_file(client: TestClient) -> None:
    """Test editing show title, author, and markdown description updates notes.md and cache."""
    shows_res = client.get("/api/shows")
    show_id = shows_res.json()["shows"][0]["show_id"]

    markdown_desc = "# Overview\n\nThis is an **amazing** audio book with *italic* text."
    edit_res = client.post(
        f"/api/shows/{show_id}/edit",
        json={
            "title": "Renamed Book Title",
            "author": "Author J.K. Smith",
            "description": markdown_desc,
        },
    )
    assert edit_res.status_code == 200
    show_data = edit_res.json()["show"]

    assert show_data["title"] == "Renamed Book Title"
    assert show_data["author"] == "Author J.K. Smith"
    assert show_data["description"] == markdown_desc
    assert "<strong>amazing</strong>" in show_data["description_html"]
    assert "<em>italic</em>" in show_data["description_html"]

    # Verify persistent notes.md file content
    from pathlib import Path

    notes_file = Path(show_data["notes_path"])
    assert notes_file.exists()
    file_content = notes_file.read_text(encoding="utf-8")
    assert 'title: "Renamed Book Title"' in file_content or 'podcast_name: "Renamed Book Title"' in file_content
    assert 'author: "Author J.K. Smith"' in file_content
    assert "**amazing**" in file_content

def test_static_app_js_track_match_logic(client: TestClient) -> None:
    """Test that static app.js includes URL-based track matching logic to prevent double-click requirement after page navigation."""
    response = client.get("/static/app.js")
    assert response.status_code == 200
    js_content = response.text
    assert "isCurrentlyLoadedTrack" in js_content
    assert "normCurrent === normTrack" in js_content
    assert "currentTrackIndex = foundIdx;" in js_content


def test_single_line_metadata_and_dark_subscribe_button(client: TestClient) -> None:
    """Test index and show detail pages render duration, track count, and added date on a single line, and Subscribe uses btn-secondary."""
    res_index = client.get("/")
    assert res_index.status_code == 200
    html_index = res_index.text

    assert 'class="meta-row"' in html_index
    assert "duration-badge" in html_index
    assert "track" in html_index
    assert "📅" in html_index
    assert 'class="btn btn-secondary"' in html_index
    assert "🎙️ Subscribe" in html_index
    assert "📋 Copy RSS" in html_index

    shows_res = client.get("/api/shows")
    show_id = shows_res.json()["shows"][0]["show_id"]
    res_show = client.get(f"/show/{show_id}")
    assert res_show.status_code == 200
    html_show = res_show.text

    assert 'class="meta-row"' in html_show
    assert "📅" in html_show
    assert 'class="btn btn-secondary"' in html_show
    assert "🎵 Tracks (" in html_show

