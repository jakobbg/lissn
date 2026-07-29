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


def test_get_cover_image(client: TestClient) -> None:
    """Test cover image endpoint serves cover file."""
    shows_res = client.get("/api/shows")
    show_id = shows_res.json()["shows"][0]["show_id"]

    response = client.get(f"/covers/{show_id}")
    assert response.status_code == 200
    assert response.headers["content-type"] in ["image/jpeg", "image/png", "image/svg+xml"]


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


def test_api_shows(client: TestClient) -> None:
    """Test REST API endpoint for shows."""
    response = client.get("/api/shows")
    assert response.status_code == 200
    data = response.json()
    assert "shows" in data
    assert data["count"] == 2


def test_api_rescan(client: TestClient) -> None:
    """Test REST API endpoint for library rescan."""
    response = client.post("/api/scan")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
