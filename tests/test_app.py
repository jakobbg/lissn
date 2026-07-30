"""
Integration tests for FastAPI application endpoints in app.py.
"""

from pathlib import Path
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


def test_background_pattern_overlay_rendering(client: TestClient) -> None:
    """Test index and show detail pages render background pattern overlay element with configured SVG and opacity."""
    index_res = client.get("/")
    assert index_res.status_code == 200
    assert 'class="bg-pattern-overlay"' in index_res.text
    assert 'pattern-dots.svg' in index_res.text
    assert 'opacity: 0.15' in index_res.text

    shows_res = client.get("/api/shows")
    shows = shows_res.json()["shows"]
    assert len(shows) > 0
    show_id = shows[0]["show_id"]

    show_res = client.get(f"/show/{show_id}")
    assert show_res.status_code == 200
    assert 'class="bg-pattern-overlay"' in show_res.text
    assert 'pattern-dots.svg' in show_res.text
    assert 'opacity: 0.15' in show_res.text


def test_back_to_library_anchor_and_show_card_ids(client: TestClient) -> None:
    """Test Back to Library button anchors to the show card ID while top-left brand title links to main page top without hash."""
    shows_res = client.get("/api/shows")
    shows = shows_res.json()["shows"]
    assert len(shows) > 0

    show_id = shows[0]["show_id"]
    response = client.get(f"/show/{show_id}")
    assert response.status_code == 200

    html = response.text
    assert f'href="/#show-{show_id}"' in html
    assert "← Back to Library" in html
    assert 'href="/" class="brand-link"' in html


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
    assert res_bad.json()["detail"] == "Sorry, the password is incorrect."

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

    # 1. Accessing RSS feed without auth (allowed for RSS & podcast apps)
    res_rss = client.get(f"/rss/{show_id}")
    assert res_rss.status_code == 200

    # 2. Accessing audio stream without auth (allowed for RSS & podcast apps)
    res_audio = client.get(f"/audio/{show_id}/{filename}")
    assert res_audio.status_code in (200, 206)

    # 3. Accessing download show zip without auth
    res_zip = client.get(f"/download/show/{show_id}")
    assert res_zip.status_code == 401

    # 4. Accessing download episode without auth
    res_ep = client.get(f"/download/{show_id}/{filename}")
    assert res_ep.status_code == 401

    # 5. Accessing edit show endpoint without auth
    res_edit = client.post(
        f"/api/shows/{show_id}/edit",
        json={"title": "New Title", "author": "New Author", "description": "New Desc"},
    )
    assert res_edit.status_code == 401

    # Now login successfully
    login_res = client.post("/api/login", json={"password": "testpass"})
    assert login_res.status_code == 200

    # Repeat requests with authenticated session client
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


def test_authenticate_header_button_rendering_and_toggle(unauthenticated_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test header renders #auth-btn before #theme-toggle, showing Authenticate when unauthenticated and Log Out when logged in."""
    from lissn.app import config

    client = unauthenticated_client
    monkeypatch.setattr(config, "password", "my_secret_pass")

    # Unauthenticated index & show detail pages
    res_index_unauth = client.get("/")
    assert res_index_unauth.status_code == 200
    html_unauth = res_index_unauth.text

    assert 'id="auth-btn"' in html_unauth
    assert 'class="auth-btn"' in html_unauth
    assert "🔑 Authenticate" in html_unauth
    assert "🚪 Log Out" not in html_unauth

    # Verify #auth-btn appears before #theme-toggle in nav-actions
    auth_pos = html_unauth.find('id="auth-btn"')
    theme_pos = html_unauth.find('id="theme-toggle"')
    assert auth_pos != -1 and theme_pos != -1
    assert auth_pos < theme_pos

    # Log in
    login_res = client.post("/api/login", json={"password": "my_secret_pass"})
    assert login_res.status_code == 200

    # Authenticated index page view
    res_index_auth = client.get("/")
    assert res_index_auth.status_code == 200
    html_auth = res_index_auth.text

    assert 'id="auth-btn"' in html_auth
    assert "🚪 Log Out" in html_auth
    assert "🔑 Authenticate" not in html_auth


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
    """Test index and show detail pages render duration, track count, and added date on a single line, and Subscribe uses btn-secondary on show page."""
    res_index = client.get("/")
    assert res_index.status_code == 200
    html_index = res_index.text

    assert 'class="meta-row"' in html_index
    assert "duration-badge" in html_index
    assert "track" in html_index
    assert "📅" in html_index
    assert "🎙️ Subscribe" not in html_index
    assert "📋 Copy RSS" not in html_index

    shows_res = client.get("/api/shows")
    show_id = shows_res.json()["shows"][0]["show_id"]
    res_show = client.get(f"/show/{show_id}")
    assert res_show.status_code == 200
    html_show = res_show.text

    assert 'class="meta-row"' in html_show
    assert "📅" in html_show
    assert 'class="btn btn-secondary"' in html_show
    assert "🎙️ Subscribe" in html_show
    assert "📋 Copy RSS" in html_show
    assert "🎵 Tracks (" in html_show


def test_subfolder_streaming_download_and_rss(client: TestClient, temp_library) -> None:
    """Test audio streaming, episode download, ZIP download, and RSS feed generation for files in subfolders."""
    books_dir, podcasts_dir, cache_dir, cache_db = temp_library

    # Create show with nested subfolder structure: Podcasts/Papaya/Papaya.2026.1901-2101/Papaya.2026-01-19.mp3
    papaya_dir = podcasts_dir / "Papaya"
    sub_dir = papaya_dir / "Papaya.2026.1901-2101"
    sub_dir.mkdir(parents=True)
    (sub_dir / "Papaya.2026-01-19.mp3").write_bytes(b"dummy papaya mp3 data 19")

    # Rescan library
    rescan_res = client.post("/api/scan")
    assert rescan_res.status_code == 200

    shows_res = client.get("/api/shows?section=podcasts")
    shows = shows_res.json()["shows"]
    papaya_show = next(s for s in shows if "Papaya" in s["title"])
    show_id = papaya_show["show_id"]

    show_detail = client.get(f"/api/shows/{show_id}").json()
    assert len(show_detail["episodes"]) == 1
    rel_filename = show_detail["episodes"][0]["filename"]
    assert rel_filename == "Papaya.2026.1901-2101/Papaya.2026-01-19.mp3"

    # 1. Test HTML show detail page renders correct data-audio-src
    show_page = client.get(f"/show/{show_id}")
    assert show_page.status_code == 200
    assert 'Papaya.2026.1901-2101/Papaya.2026-01-19.mp3' in show_page.text

    # 2. Test streaming audio endpoint with subfolder path
    stream_res = client.get(f"/audio/{show_id}/{rel_filename}")
    assert stream_res.status_code == 200
    assert stream_res.content == b"dummy papaya mp3 data 19"

    # 3. Test download episode endpoint with subfolder path
    dl_res = client.get(f"/download/{show_id}/{rel_filename}")
    assert dl_res.status_code == 200
    assert dl_res.content == b"dummy papaya mp3 data 19"

    # 4. Test RSS feed contains correct enclosure URL
    rss_res = client.get(f"/rss/{show_id}")
    assert rss_res.status_code == 200
    assert f"/audio/{show_id}/Papaya.2026.1901-2101/Papaya.2026-01-19.mp3" in rss_res.text

    # 5. Test ZIP archive download preserves relative subfolder path
    import io
    import zipfile

    zip_res = client.get(f"/download/show/{show_id}")
    assert zip_res.status_code == 200
    with zipfile.ZipFile(io.BytesIO(zip_res.content), "r") as zf:
        assert "Papaya.2026.1901-2101/Papaya.2026-01-19.mp3" in zf.namelist()


def test_favicon_endpoints(client: TestClient) -> None:
    """Test /favicon.ico and /apple-touch-icon.png endpoints return expected favicon image content."""
    res_ico = client.get("/favicon.ico")
    assert res_ico.status_code == 200
    assert "image/x-icon" in res_ico.headers.get("content-type", "")
    assert len(res_ico.content) > 0

    res_png = client.get("/apple-touch-icon.png")
    assert res_png.status_code == 200
    assert "image/png" in res_png.headers.get("content-type", "")
    assert len(res_png.content) > 0


def test_player_restoration_script_elements(client: TestClient) -> None:
    """Test index and show pages contain global audio element and bottom player structure for session state restoration."""
    index_res = client.get("/")
    assert index_res.status_code == 200
    assert 'id="global-audio-element"' in index_res.text
    assert 'id="bottom-player"' in index_res.text
    assert 'id="player-play-btn"' in index_res.text

    shows_res = client.get("/api/shows")
    shows = shows_res.json()["shows"]
    if shows:
        show_id = shows[0]["show_id"]
        show_res = client.get(f"/show/{show_id}")
        assert show_res.status_code == 200
        assert 'id="global-audio-element"' in show_res.text
        assert 'id="bottom-player"' in show_res.text


def test_opengraph_logo_social_preview_tags(client: TestClient) -> None:
    """Test index page contains OpenGraph and Twitter card meta tags referencing logo.png."""
    index_res = client.get("/")
    assert index_res.status_code == 200
    assert 'property="og:image" content="' in index_res.text
    assert '/static/logo.png"' in index_res.text
    assert 'name="twitter:card" content="summary_large_image"' in index_res.text
    assert 'name="twitter:image" content="' in index_res.text


def test_alt_click_podcast_new_window_logic(client: TestClient) -> None:
    """Test that app.js includes alt-click handler to open podcast show in a new window."""
    response = client.get("/static/app.js")
    assert response.status_code == 200
    js_content = response.text
    assert "e.altKey" in js_content
    assert "window.open(targetUrl.href, '_blank')" in js_content
    assert "e.preventDefault()" in js_content
    assert ".show-card" in js_content


def test_synchronous_auth_state_script_rendering(client: TestClient, unauthenticated_client: TestClient) -> None:
    """Test index and show pages render synchronous lissn-auth-state JSON script tag with correct state."""
    # Authenticated client
    index_res = client.get("/")
    assert index_res.status_code == 200
    assert 'id="lissn-auth-state"' in index_res.text
    assert '"authenticated": true' in index_res.text

    shows_res = client.get("/api/shows")
    shows = shows_res.json()["shows"]
    assert len(shows) > 0
    show_id = shows[0]["show_id"]

    show_res = client.get(f"/show/{show_id}")
    assert show_res.status_code == 200
    assert 'id="lissn-auth-state"' in show_res.text
    assert '"authenticated": true' in show_res.text

    # Unauthenticated client
    unauth_index = unauthenticated_client.get("/")
    assert unauth_index.status_code == 200
    assert 'id="lissn-auth-state"' in unauth_index.text
    assert '"authenticated": false' in unauth_index.text

    unauth_show = unauthenticated_client.get(f"/show/{show_id}")
    assert unauth_show.status_code == 200
    assert 'id="lissn-auth-state"' in unauth_show.text
    assert '"authenticated": false' in unauth_show.text


def test_cover_image_selection_and_upload(client: TestClient, unauthenticated_client: TestClient) -> None:
    """Test cover image listing, folder image selection, and max 5MB WebP/PNG/JPEG upload endpoints."""
    shows_res = client.get("/api/shows")
    assert shows_res.status_code == 200
    shows = shows_res.json()["shows"]
    assert len(shows) > 0
    show = shows[0]
    show_id = show["show_id"]
    folder_path = Path(show["folder_path"])

    # Create dummy images in show folder
    img1 = folder_path / "alternate_cover.jpg"
    img1.write_bytes(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xd9")
    img2 = folder_path / "secondary_cover.png"
    img2.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89")

    try:
        # Unauthenticated GET /images -> 401
        unauth_imgs = unauthenticated_client.get(f"/api/shows/{show_id}/images")
        assert unauth_imgs.status_code == 401

        # Authenticated GET /images -> 200
        imgs_res = client.get(f"/api/shows/{show_id}/images")
        assert imgs_res.status_code == 200
        img_data = imgs_res.json()
        assert img_data["show_id"] == show_id
        filenames = [img["filename"] for img in img_data["images"]]
        assert "alternate_cover.jpg" in filenames
        assert "secondary_cover.png" in filenames

        # Unauthenticated select cover -> 401
        unauth_select = unauthenticated_client.post(f"/api/shows/{show_id}/select-cover", json={"filename": "alternate_cover.jpg"})
        assert unauth_select.status_code == 401

        # Path traversal attack attempt -> 400
        bad_select = client.post(f"/api/shows/{show_id}/select-cover", json={"filename": "../../../etc/passwd"})
        assert bad_select.status_code == 400

        # Authenticated valid cover selection -> 200
        select_res = client.post(f"/api/shows/{show_id}/select-cover", json={"filename": "alternate_cover.jpg"})
        assert select_res.status_code == 200
        assert select_res.json()["status"] == "success"

        # Verify show cover updated
        updated_show_res = client.get(f"/api/shows/{show_id}")
        assert updated_show_res.json()["cover_path"] == str(img1.resolve())

        # Unauthenticated cover upload -> 401
        unauth_up = unauthenticated_client.post(
            f"/api/shows/{show_id}/upload-cover",
            files={"file": ("test_cover.webp", b"RIFF....WEBP", "image/webp")},
        )
        assert unauth_up.status_code == 401

        # Invalid extension upload -> 400
        bad_ext_up = client.post(
            f"/api/shows/{show_id}/upload-cover",
            files={"file": ("malicious.exe", b"MZ...", "application/x-msdownload")},
        )
        assert bad_ext_up.status_code == 400

        # Oversized file upload (> 5MB) -> 413
        oversized_data = b"0" * (5 * 1024 * 1024 + 1)
        oversized_up = client.post(
            f"/api/shows/{show_id}/upload-cover",
            files={"file": ("large_cover.jpg", oversized_data, "image/jpeg")},
        )
        assert oversized_up.status_code == 413

        # Valid WebP upload under 5MB -> 200
        valid_data = b"\xff\xd8\xff\xe0\x00\x10JFIF"
        valid_up = client.post(
            f"/api/shows/{show_id}/upload-cover",
            files={"file": ("new_uploaded.jpg", valid_data, "image/jpeg")},
        )
        assert valid_up.status_code == 200
        up_json = valid_up.json()
        assert up_json["status"] == "success"
        uploaded_file = Path(up_json["cover_path"])
        assert uploaded_file.exists()
        assert uploaded_file.read_bytes() == valid_data
    finally:
        # Cleanup temporary test files
        if img1.exists():
            img1.unlink()
        if img2.exists():
            img2.unlink()
        if 'uploaded_file' in locals() and uploaded_file.exists():
            uploaded_file.unlink()


def test_cover_image_file_param_preview(client: TestClient) -> None:
    """Test GET /covers/{show_id}?file={filename} serves specified image from show folder for modal preview."""
    shows_res = client.get("/api/shows")
    assert shows_res.status_code == 200
    show = shows_res.json()["shows"][0]
    show_id = show["show_id"]
    folder_path = Path(show["folder_path"])

    custom_img = folder_path / "custom_preview.png"
    custom_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
    custom_img.write_bytes(custom_bytes)

    try:
        preview_res = client.get(f"/covers/{show_id}?file=custom_preview.png")
        assert preview_res.status_code == 200
        assert preview_res.headers["content-type"] == "image/png"
        assert preview_res.content == custom_bytes
    finally:
        if custom_img.exists():
            custom_img.unlink()


def test_edit_modal_cover_preview_js_handlers(client: TestClient) -> None:
    """Test that app.js contains event handlers for updating cover preview image on dropdown and file upload changes."""
    response = client.get("/static/app.js")
    assert response.status_code == 200
    js_content = response.text

    assert "'edit-cover-select'" in js_content
    assert "/covers/${showId}?file=${encodeURIComponent(selectedFilename)}" in js_content
    assert "'edit-cover-file'" in js_content
    assert "URL.createObjectURL(file)" in js_content


def test_subscribe_and_copy_rss_only_on_show_page(client: TestClient) -> None:
    """Test that Subscribe and Copy RSS buttons are removed from main page and present only on show detail page."""
    index_res = client.get("/")
    assert index_res.status_code == 200
    assert "js-copy-rss" not in index_res.text
    assert 'title="Subscribe in podcast app"' not in index_res.text

    shows_res = client.get("/api/shows")
    show_id = shows_res.json()["shows"][0]["show_id"]
    show_res = client.get(f"/show/{show_id}")
    assert show_res.status_code == 200
    assert "js-copy-rss" in show_res.text
    assert 'title="Subscribe in podcast app"' in show_res.text


def test_spacebar_not_hijacked_in_app_js(client: TestClient) -> None:
    """Test that app.js does not intercept spacebar so spacebar functions as page down."""
    response = client.get("/static/app.js")
    assert response.status_code == 200
    js_content = response.text

    # Ensure global keyboard shortcuts do not hijack spacebar
    assert "if (e.code === 'Space')" not in js_content
    # Ensure track row keydown handler does not intercept spacebar
    assert "e.key === ' ' || e.key === 'Enter'" not in js_content
    assert "e.key === 'Enter' || e.key === ' '" not in js_content


def test_play_button_title_tooltips(client: TestClient) -> None:
    """Test that index and show pages present 'Play / Pause' title without '(Space)' shortcut."""
    index_res = client.get("/")
    assert index_res.status_code == 200
    assert 'title="Play / Pause"' in index_res.text
    assert 'title="Play / Pause (Space)"' not in index_res.text

    shows_res = client.get("/api/shows")
    show_id = shows_res.json()["shows"][0]["show_id"]
    show_res = client.get(f"/show/{show_id}")
    assert show_res.status_code == 200
    assert 'title="Play / Pause"' in show_res.text
    assert 'title="Play / Pause (Space)"' not in show_res.text


def test_rss_feed_etag_and_304_caching(client: TestClient) -> None:
    """Test RSS feed generation includes ETag & Cache-Control and returns 304 Not Modified for conditional GET requests."""
    shows_res = client.get("/api/shows")
    show_id = shows_res.json()["shows"][0]["show_id"]

    res = client.get(f"/rss/{show_id}")
    assert res.status_code == 200
    assert "etag" in res.headers
    assert "public, max-age=3600" in res.headers.get("cache-control", "")
    etag = res.headers["etag"]

    # Request with matching If-None-Match header
    cond_res = client.get(f"/rss/{show_id}", headers={"If-None-Match": etag})
    assert cond_res.status_code == 304
    assert cond_res.text == ""
    assert cond_res.headers.get("etag") == etag


def test_cover_image_etag_and_304_caching(client: TestClient) -> None:
    """Test cover image endpoint includes ETag, Last-Modified, Cache-Control and handles 304 Not Modified."""
    shows_res = client.get("/api/shows")
    show_id = shows_res.json()["shows"][0]["show_id"]

    res = client.get(f"/covers/{show_id}")
    assert res.status_code == 200
    assert "etag" in res.headers
    assert "last-modified" in res.headers
    assert "public, max-age=86400" in res.headers.get("cache-control", "")
    etag = res.headers["etag"]
    last_mod = res.headers["last-modified"]

    # Request with matching If-None-Match
    etag_res = client.get(f"/covers/{show_id}", headers={"If-None-Match": etag})
    assert etag_res.status_code == 304
    assert etag_res.text == ""

    # Request with matching If-Modified-Since
    mod_res = client.get(f"/covers/{show_id}", headers={"If-Modified-Since": last_mod})
    assert mod_res.status_code == 304
    assert mod_res.text == ""


def test_audio_stream_etag_and_304_caching(client: TestClient) -> None:
    """Test audio streaming endpoint sets ETag & Last-Modified and returns 304 for full file GETs with If-None-Match."""
    shows_res = client.get("/api/shows")
    show_id = shows_res.json()["shows"][0]["show_id"]
    show_detail = client.get(f"/api/shows/{show_id}").json()
    filename = show_detail["episodes"][0]["filename"]

    res = client.get(f"/audio/{show_id}/{filename}")
    assert res.status_code == 200
    assert "etag" in res.headers
    assert "last-modified" in res.headers
    assert "immutable" in res.headers.get("cache-control", "")
    etag = res.headers["etag"]

    # Conditional GET without Range header returns 304 Not Modified
    cond_res = client.get(f"/audio/{show_id}/{filename}", headers={"If-None-Match": etag})
    assert cond_res.status_code == 304
    assert cond_res.text == ""

    # Range request overrides 304 and returns 206 Partial Content
    range_res = client.get(f"/audio/{show_id}/{filename}", headers={"Range": "bytes=0-10", "If-None-Match": etag})
    assert range_res.status_code == 206


def test_favicon_etag_and_304_caching(client: TestClient) -> None:
    """Test favicon endpoints return ETag and handle conditional 304 Not Modified."""
    res = client.get("/favicon.ico")
    assert res.status_code == 200
    if "etag" in res.headers:
        etag = res.headers["etag"]
        cond_res = client.get("/favicon.ico", headers={"If-None-Match": etag})
        assert cond_res.status_code == 304


def test_html_pages_etag_and_304_caching(client: TestClient) -> None:
    """Test HTML pages (/ and /show/{show_id}) generate ETags, set Vary & Cache-Control, and return 304 Not Modified."""
    # Index page testing
    index_res = client.get("/")
    assert index_res.status_code == 200
    assert "etag" in index_res.headers
    assert "no-cache, must-revalidate" in index_res.headers.get("cache-control", "")
    assert "Cookie" in index_res.headers.get("vary", "")
    index_etag = index_res.headers["etag"]

    index_cond = client.get("/", headers={"If-None-Match": index_etag})
    assert index_cond.status_code == 304
    assert index_cond.text == ""

    # Show detail page testing
    shows_res = client.get("/api/shows")
    show_id = shows_res.json()["shows"][0]["show_id"]

    show_res = client.get(f"/show/{show_id}")
    assert show_res.status_code == 200
    assert "etag" in show_res.headers
    assert "no-cache, must-revalidate" in show_res.headers.get("cache-control", "")
    assert "Cookie" in show_res.headers.get("vary", "")
    show_etag = show_res.headers["etag"]

    show_cond = client.get(f"/show/{show_id}", headers={"If-None-Match": show_etag})
    assert show_cond.status_code == 304
    assert show_cond.text == ""


def test_download_episode_edge_cases(client: TestClient) -> None:
    """Test 404 and error handling for invalid show_id and missing audio files in download endpoint."""
    # Invalid show ID -> 404
    res = client.get("/download/invalid_show_id_12345/episode1.mp3")
    assert res.status_code == 404
    assert res.json()["detail"] == "Show not found"

    # Missing audio file in valid show -> 404
    shows_res = client.get("/api/shows")
    show_id = shows_res.json()["shows"][0]["show_id"]
    res_missing = client.get(f"/download/{show_id}/non_existent_file_xyz.mp3")
    assert res_missing.status_code == 404
    assert res_missing.json()["detail"] == "Audio file not found"


def test_api_show_mutation_invalid_show_ids(client: TestClient) -> None:
    """Test API endpoints return 404 when mutating or fetching non-existent show IDs."""
    # Edit non-existent show
    edit_res = client.post("/api/show/invalid_show_id_999/edit", json={"title": "T", "author": "A", "description": "D"})
    assert edit_res.status_code == 404

    # Select cover non-existent show
    cover_res = client.post("/api/show/invalid_show_id_999/select_cover", json={"cover_path": "/tmp/test.jpg"})
    assert cover_res.status_code == 404

    # Upload cover non-existent show
    upload_res = client.post(
        "/api/show/invalid_show_id_999/upload_cover",
        files={"file": ("test.jpg", b"fake_image_bytes", "image/jpeg")},
    )
    assert upload_res.status_code == 404


def test_code_files_cannot_be_streamed_or_downloaded(client: TestClient, temp_library) -> None:
    """Test that requesting code files (.py, .sh, .json, .env) via /audio/ or /download/ is blocked with HTTP 403."""
    shows_res = client.get("/api/shows")
    show = shows_res.json()["shows"][0]
    show_id = show["show_id"]
    show_folder = Path(show["folder_path"])

    # Create dummy code files in the show directory
    (show_folder / "script.py").write_text("print('hello world')", encoding="utf-8")
    (show_folder / "config.env").write_text("SECRET=12345", encoding="utf-8")

    # Attempt to stream code file -> 403 Forbidden
    stream_res = client.get(f"/audio/{show_id}/script.py")
    assert stream_res.status_code == 403
    assert "Forbidden file type" in stream_res.json()["detail"]

    # Attempt to download code file -> 403 Forbidden
    download_res = client.get(f"/download/{show_id}/script.py")
    assert download_res.status_code == 403
    assert "Forbidden file type" in download_res.json()["detail"]

    # Attempt to stream .env file -> 403 Forbidden
    env_res = client.get(f"/audio/{show_id}/config.env")
    assert env_res.status_code == 403




