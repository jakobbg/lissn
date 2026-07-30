<p align="center">
  <img src="src/lissn/static/logo.png" alt="lissn logo" width="220">
</p>

<p align="center">
  <b>Personal Audio Books &amp; Podcasts Server with RSS Feed Support</b>
</p>

---

> ⚠️ **IMPORTANT LEGAL NOTICE**
> 
> **lissn** is intended exclusively for indexing, streaming, and subscribing to **your own legally owned media files**. 
> Do **not** use this software to index, host, or share illegally downloaded files, pirated audiobooks, or copyrighted content that you do not own or have explicit legal rights to distribute.

---

## 🌟 Key Features

- **Folder Indexing & Fast Startup**: Indexes `Books` and `Podcasts` media directories with fast incremental caching. Supports configurable scan modes (`incremental`, `async`, `manual`, `full`).
- **Unauthenticated Podcast RSS 2.0 Feeds**: Generates valid, iTunes-compatible podcast XML feeds for 1-click subscription in podcast apps (`podcast://` protocol, Apple Podcasts, Pocket Casts, Overcast) without requiring session authentication.
- **HTTP Byte-Range Audio Streaming & Conditional Caching**: Progressive seeking (`HTTP 206 Partial Content`) and HTTP conditional headers (`ETag`, `304 Not Modified`) across `.mp3`, `.m4a`, `.m4b`, `.aac`, `.flac`, `.ogg`, `.opus`, and `.wav` formats.
- **On-the-Fly ZIP Archives**: Streams complete show downloads as custom-named ZIP files (`title - author/publisher.zip`) via `zipstream-ng`, featuring a warning modal for archives over 100MB.
- **SQLite Database Persistence**: All show metadata (title, author, publisher, description, HTML rendering) and custom cover artwork BLOBs persist cleanly inside SQLite (`data/lissn_cache.db`).
- **Real-Time Library Search**: Instant client-side search filter on the main index page for matching show title, author, or publisher.
- **Custom Cover Artwork Management**: Upload custom cover images (WebP/PNG/JPEG up to 5MB), pick from images in the show directory, or preview artwork in a zoom modal. Dynamic background gradient adapts to active cover art colors.
- **Responsive & Accessible Interface**: Framework-free vanilla JS UI with auto-detecting Light/Dark mode, bottom player state persistence across page navigation, keyboard shortcuts (`s`, `c`, `r`, `e`, `d`, `?`), backdrop click modal dismissal, and OpenGraph social preview cards (`/show/{show_id}`).
- **Strict Security**: Streaming and download endpoints enforce strict file extension allowlists to prevent access to non-audio files. Administrative management endpoints are protected by session password authentication.

---

## 🚀 Quick Start & Installation

### Prerequisites
- **Python 3.10+** (supported on FreeBSD, Linux, and macOS)

### 1. Clone & Setup Virtual Environment
```bash
git clone https://github.com/jakobbg/lissn.git
cd lissn
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install Package
```bash
pip install -e ".[dev]"
```

> **FreeBSD Note**: Install system dependencies via `sudo pkg install py312-fastapi py312-pydantic py312-uvicorn py312-pillow py312-Jinja2 py312-markdown py312-mutagen py312-pyyaml py312-h2 py312-python-multipart py312-pytest py312-httpx py312-pytest-cov`, then initialize venv with `--system-site-packages`. (`python-multipart` is required for cover art upload support).

### 3. Configure
Copy example config to `config/lissn.json`:
```bash
cp config/lissn.example.json config/lissn.json
```

Edit `config/lissn.json` to point to your media directories:
```json
{
  "books_dir": "/path/to/your/Books",
  "podcasts_dir": "/path/to/your/Podcasts",
  "host": "0.0.0.0",
  "port": 8000,
  "base_url": "http://localhost:8000"
}
```

### 4. Start Application
```bash
python3 -m lissn.app
```
Navigate to `http://localhost:8000` in your browser.

---

## 🧪 Testing & Code Coverage

**lissn** maintains a comprehensive automated test suite (`pytest` + `pytest-cov`) covering API endpoints, RSS feed generation, HTTP range streaming, authentication, conditional ETag caching, and file security restrictions.

See the complete [Testing & Code Quality Guide](docs/testing.md) for details.

### Run Test Suite
```bash
python3 -m pytest
```

### Run Test Suite with Coverage Report (requires pytest-cov)
```bash
python3 -m pytest --cov=lissn --cov-report=term-missing
```

---

## 🔒 Production Deployment & Services

For running **lissn** as a service daemon on **FreeBSD** (`rc.d`) or **Linux** (`systemd`) with automatic logging to `./logs/lissn.log`, see the [Running lissn as a Service Guide](docs/service.md).

In production, run **lissn** behind a reverse proxy for HTTPS termination:

### Caddy (Recommended)
```caddyfile
lissn.example.com {
    reverse_proxy localhost:8000
}
```

### Tailscale Serve (Private Network)
```bash
tailscale serve https / http://localhost:8000
```

### Nginx
```nginx
server {
    listen 443 ssl http2;
    server_name lissn.example.com;

    ssl_certificate /etc/letsencrypt/live/lissn.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/lissn.example.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```


---

## 🛠️ Local Development & Debugging

### 1. Seed Sample Media Library
Populate `./data/Books` and `./data/Podcasts` with test audio files and cover art:
```bash
python scripts/seed_dev_data.py
```

### 2. IDE Debugging (VS Code / Cursor)
The repository includes `.vscode/launch.json` pre-configured for `F5` debugging:
- **`lissn: Run & Debug Web Server`**: Debug web server at `http://localhost:8000`.
- **`pytest: Debug All Tests`**: Debug the automated test suite.

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for details.
