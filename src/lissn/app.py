"""
FastAPI Web Application for lissn.
Serves index pages, show detail views with OpenGraph meta tags,
podcast RSS 2.0 feeds, audio file streaming, and JSON APIs.
"""

import hashlib
import io
import mimetypes
from pathlib import Path
from typing import Any, Dict, Optional
import zipfile

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from lissn.colors import get_show_colors
from lissn.config import Config
from lissn.rss import generate_rss_feed
from lissn.scanner import LibraryScanner

# Register audio MIME types for audiobook and podcast formats
mimetypes.add_type("audio/mp4", ".m4b")
mimetypes.add_type("audio/mp4", ".m4a")
mimetypes.add_type("audio/mpeg", ".mp3")
mimetypes.add_type("audio/ogg", ".ogg")
mimetypes.add_type("audio/opus", ".opus")
mimetypes.add_type("audio/flac", ".flac")
mimetypes.add_type("audio/wav", ".wav")
mimetypes.add_type("audio/aac", ".aac")

app = FastAPI(
    title="lissn",
    description="Audiobook and Podcast Indexer & RSS Feed Generator",
    version="0.3.0",
)

config = Config()
config.ensure_directories()

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
templates.env.filters["urlencode"] = lambda s: quote(str(s), safe="/")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


@app.get("/favicon.ico", include_in_schema=False)
def favicon_ico() -> FileResponse:
    """Serve binary ICO favicon for browsers."""
    return FileResponse(
        BASE_DIR / "static" / "favicon.ico",
        media_type="image/x-icon",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@app.get("/apple-touch-icon.png", include_in_schema=False)
def apple_touch_icon() -> FileResponse:
    """Serve high-DPI apple-touch-icon for iOS home screen shortcuts."""
    return FileResponse(
        BASE_DIR / "static" / "apple-touch-icon.png",
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=86400"},
    )


scanner = LibraryScanner(
    books_dir=config.books_dir,
    podcasts_dir=config.podcasts_dir,
    cache_dir=config.cache_dir,
    db_path=config.cache_db_path,
    max_episodes_per_show=config.max_episodes_per_show,
)


def generate_session_token(password: str) -> str:
    """Generate deterministic session token derived from server password."""
    if not password:
        return ""
    return hashlib.sha256(f"lissn_session_token:{password}".encode("utf-8")).hexdigest()


def is_authenticated(request: Request) -> bool:
    """Check if request contains valid session cookie or authorization token."""
    if not config.password:
        return True

    expected = generate_session_token(config.password)
    cookie_token = request.cookies.get("lissn_session")
    if cookie_token and cookie_token == expected:
        return True

    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer ") and auth_header[7:].strip() == expected:
        return True

    x_token = request.headers.get("X-Lissn-Session")
    if x_token and x_token == expected:
        return True

    return False


def require_auth(request: Request) -> None:
    """Enforce session authentication if password is configured."""
    if not is_authenticated(request):
        raise HTTPException(
            status_code=401,
            detail="Sorry, the password is incorrect.",
            headers={"WWW-Authenticate": "Bearer"},
        )


class LoginRequest(BaseModel):
    password: str


class EditShowRequest(BaseModel):
    title: str
    author: str = ""
    description: str = ""


@app.middleware("http")
async def add_protocol_security_headers(request: Request, call_next):
    """Middleware attaching modern web protocol and security headers to HTTP responses."""
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    return response


from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    """Perform initial library scan on application startup."""
    scanner.scan_all()
    yield

app.router.lifespan_context = lifespan


def get_base_url(request: Request) -> str:
    """Determine absolute base URL from HTTP request or configuration."""
    if config.base_url and "localhost" not in config.base_url:
        return config.base_url.rstrip("/")
    return str(request.base_url).rstrip("/")


def get_host_header(request: Request) -> str:
    """Extract host header string for podcast:// protocol URLs."""
    return request.headers.get("host") or f"{config.host}:{config.port}"


@app.get("/", response_class=HTMLResponse)
@app.head("/", response_class=HTMLResponse)
def index_page(request: Request) -> Response:
    """Front page displaying indexed Books and Podcasts with filter tabs."""
    books = scanner.cache.get_all_shows(section="books")
    podcasts = scanner.cache.get_all_shows(section="podcasts")

    return templates.TemplateResponse(
        request,
        "index.html",
        context={
            "books": books,
            "podcasts": podcasts,
            "base_url": get_base_url(request),
            "host_header": get_host_header(request),
            "authenticated": is_authenticated(request),
            "password_required": bool(config.password),
            "pattern_name": config.pattern_name,
            "pattern_opacity": config.pattern_opacity,
        },
    )


@app.get("/show/{show_id}", response_class=HTMLResponse)
@app.head("/show/{show_id}", response_class=HTMLResponse)
def show_detail_page(show_id: str, request: Request) -> Response:
    """Show detail page with tracks and OpenGraph meta tags for social media sharing."""
    show = scanner.cache.get_show(show_id)
    if not show:
        raise HTTPException(status_code=404, detail="Show not found")

    cover_path = Path(show["cover_path"]) if show.get("cover_path") else None
    colors = get_show_colors(cover_path, show["show_id"])

    return templates.TemplateResponse(
        request,
        "show.html",
        context={
            "show": show,
            "show_colors": colors,
            "base_url": get_base_url(request),
            "host_header": get_host_header(request),
            "authenticated": is_authenticated(request),
            "password_required": bool(config.password),
            "pattern_name": config.pattern_name,
            "pattern_opacity": config.pattern_opacity,
        },
    )


@app.get("/covers/{show_id}")
@app.head("/covers/{show_id}")
def get_cover_image(show_id: str) -> Response:
    """Serve cover art image for a show with byte range and HEAD support."""
    show = scanner.cache.get_show(show_id)
    if not show or not show.get("cover_path"):
        # Return fallback SVG cover image
        svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" width="600" height="600" viewBox="0 0 600 600">
            <rect width="600" height="600" fill="#1e293b"/>
            <text x="300" y="280" font-size="72" text-anchor="middle" fill="#6366f1">🎧</text>
            <text x="300" y="360" font-size="28" font-weight="bold" text-anchor="middle" fill="#f8fafc">
                {show['title'] if show else 'lissn'}
            </text>
        </svg>"""
        return Response(content=svg_content, media_type="image/svg+xml", headers={"Accept-Ranges": "bytes"})

    cover_file = Path(show["cover_path"])
    if not cover_file.exists():
        raise HTTPException(status_code=404, detail="Cover image file not found")

    suffix = cover_file.suffix.lower()
    media_type = "image/jpeg"
    if suffix in [".png"]:
        media_type = "image/png"
    elif suffix in [".webp"]:
        media_type = "image/webp"

    return FileResponse(path=cover_file, media_type=media_type, headers={"Accept-Ranges": "bytes"})


from urllib.parse import quote, unquote

@app.get("/audio/{show_id}/{filename:path}")
@app.head("/audio/{show_id}/{filename:path}")
def stream_audio(show_id: str, filename: str, request: Request) -> Response:
    """Stream audio file supporting partial HTTP range requests (206/416) and HEAD method."""
    require_auth(request)
    show = scanner.cache.get_show(show_id)
    if not show:
        raise HTTPException(status_code=404, detail="Show not found")

    folder = Path(show["folder_path"])
    audio_file = (folder / filename).resolve()
    if not audio_file.exists():
        audio_file = (folder / unquote(filename)).resolve()

    if not audio_file.exists() or not audio_file.is_file():
        # Fallback check across show episodes for matching filename or file_path
        for ep in show.get("episodes", []):
            if (
                ep.get("filename") == filename
                or ep.get("filename") == unquote(filename)
                or Path(ep.get("filename", "")).name == filename
                or Path(ep.get("filename", "")).name == unquote(filename)
            ):
                cand = Path(ep["file_path"]).resolve()
                if cand.exists() and cand.is_file():
                    audio_file = cand
                    break

    # Prevent directory traversal attacks
    if not str(audio_file).startswith(str(folder.resolve())):
        raise HTTPException(status_code=403, detail="Forbidden file path")

    if not audio_file.exists() or not audio_file.is_file():
        raise HTTPException(status_code=404, detail="Audio file not found")

    guessed_type, _ = mimetypes.guess_type(audio_file.name)
    media_type = guessed_type or "audio/mpeg"

    return FileResponse(
        path=audio_file,
        media_type=media_type,
        headers={"Accept-Ranges": "bytes"},
    )


@app.get("/download/show/{show_id}")
def download_show_zip(show_id: str, request: Request) -> Response:
    """Download all audio files for a show bundled into a single ZIP archive."""
    require_auth(request)
    show = scanner.cache.get_show(show_id)
    if not show or not show.get("episodes"):
        raise HTTPException(status_code=404, detail="Show or tracks not found")

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for ep in show["episodes"]:
            ep_path = Path(ep["file_path"])
            if ep_path.is_file():
                zf.write(ep_path, arcname=ep["filename"])

    buffer.seek(0)
    # Sanitize title for filename while preserving Unicode letters
    safe_title = "".join(c for c in show["title"] if c.isalnum() or c in (" ", "_", "-")).strip() or "show"
    zip_filename = f"{safe_title}.zip"
    encoded_filename = quote(zip_filename)

    return Response(
        content=buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{safe_title}.zip"; filename*=UTF-8\'\'{encoded_filename}'},
    )


@app.get("/download/{show_id}/{filename:path}")
@app.head("/download/{show_id}/{filename:path}")
def download_episode(show_id: str, filename: str, request: Request) -> Response:
    """Download a single episode file with Content-Disposition attachment header."""
    require_auth(request)
    show = scanner.cache.get_show(show_id)
    if not show:
        raise HTTPException(status_code=404, detail="Show not found")

    folder = Path(show["folder_path"])
    audio_file = (folder / filename).resolve()
    if not audio_file.exists():
        audio_file = (folder / unquote(filename)).resolve()

    if not audio_file.exists() or not audio_file.is_file():
        # Fallback check across show episodes for matching filename or file_path
        for ep in show.get("episodes", []):
            if (
                ep.get("filename") == filename
                or ep.get("filename") == unquote(filename)
                or Path(ep.get("filename", "")).name == filename
                or Path(ep.get("filename", "")).name == unquote(filename)
            ):
                cand = Path(ep["file_path"]).resolve()
                if cand.exists() and cand.is_file():
                    audio_file = cand
                    break

    # Prevent directory traversal attacks
    if not str(audio_file).startswith(str(folder.resolve())):
        raise HTTPException(status_code=403, detail="Forbidden file path")

    if not audio_file.exists() or not audio_file.is_file():
        raise HTTPException(status_code=404, detail="Audio file not found")

    guessed_type, _ = mimetypes.guess_type(audio_file.name)
    media_type = guessed_type or "audio/mpeg"
    safe_ascii_name = "".join(c for c in audio_file.name if c.isascii() and c not in '"\\').strip() or "audio"
    encoded_filename = quote(audio_file.name)

    return FileResponse(
        path=audio_file,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{safe_ascii_name}"; filename*=UTF-8\'\'{encoded_filename}'},
    )


@app.get("/rss/{show_id}")
@app.head("/rss/{show_id}")
def get_podcast_rss(show_id: str, request: Request) -> Response:
    """Generate and return RSS 2.0 Podcast XML feed for a show."""
    show = scanner.cache.get_show(show_id)
    if not show:
        raise HTTPException(status_code=404, detail="Show not found")

    rss_xml = generate_rss_feed(show_data=show, base_url=get_base_url(request))
    return Response(content=rss_xml, media_type="application/rss+xml")


@app.get("/api/shows")
def api_get_shows(section: str = None) -> Response:
    """REST API endpoint returning indexed shows."""
    shows = scanner.cache.get_all_shows(section=section)
    return {"shows": shows, "count": len(shows)}


@app.get("/api/shows/{show_id}")
def api_get_show(show_id: str) -> Response:
    """REST API endpoint returning detailed show information."""
    show = scanner.cache.get_show(show_id)
    if not show:
        raise HTTPException(status_code=404, detail="Show not found")
    return show


@app.post("/api/shows/{show_id}/edit")
def api_edit_show(show_id: str, payload: EditShowRequest, request: Request) -> Dict[str, Any]:
    """REST API endpoint to update show title, author, and markdown description."""
    require_auth(request)

    updated_show = scanner.update_show_metadata(
        show_id=show_id,
        title=payload.title,
        author=payload.author,
        description=payload.description,
    )
    if not updated_show:
        raise HTTPException(status_code=404, detail="Show not found")
    return {"status": "success", "show": updated_show}


@app.post("/api/login")
def api_login(payload: LoginRequest, response: Response) -> Dict[str, Any]:
    """Authenticate user with password and set session cookie."""
    if not config.password or payload.password == config.password:
        token = generate_session_token(config.password)
        response.set_cookie(
            key="lissn_session",
            value=token,
            httponly=True,
            samesite="lax",
            path="/",
        )
        return {"status": "success", "authenticated": True, "token": token}

    raise HTTPException(status_code=401, detail="Sorry, the password is incorrect.")


@app.post("/api/logout")
def api_logout(response: Response) -> Dict[str, Any]:
    """Clear session cookie and log out."""
    response.delete_cookie(key="lissn_session", path="/")
    return {"status": "success", "authenticated": False}


@app.get("/api/auth/status")
def api_auth_status(request: Request) -> Dict[str, Any]:
    """Check current authentication status and password requirement."""
    return {
        "authenticated": is_authenticated(request),
        "password_required": bool(config.password),
    }


@app.post("/api/scan")
def api_rescan_library() -> Response:
    """REST API endpoint to trigger full library rescan."""
    result = scanner.scan_all()
    return {"status": "success", "scanned": result}


if __name__ == "__main__":
    import uvicorn

    # Run Uvicorn ASGI server with HTTP/2 and modern web protocol standards
    uvicorn.run(
        "lissn.app:app",
        host=config.host,
        port=config.port,
        http="auto",
    )
