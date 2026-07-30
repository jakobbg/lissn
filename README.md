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

- **Folder Indexing**: Automatically scans directories for **Audio Books** (`.../Books`) and **Podcasts** (`.../Podcasts`).
- **Podcast RSS 2.0 Feeds**: Generates valid, iTunes-compatible podcast XML feeds for 1-click subscription in podcast apps (`podcast://` protocol).
- **HTTP Byte-Range Audio Streaming**: Supports progressive seeking (`HTTP 206 Partial Content`) across `.mp3`, `.m4a`, `.m4b`, `.aac`, `.flac`, `.ogg`, `.opus`, and `.wav` formats.
- **Strict File Security**: Audio streaming and download endpoints enforce strict extension allowlists to ensure non-audio files (such as code or configuration files) can never be accessed.
- **Per-Show Metadata (`notes.md`)**: Auto-generates `notes.md` allowing custom `title`, `author`, `podcast_name`, and rich Markdown descriptions.
- **Social Preview Share Cards**: Show pages (`/show/{show_id}`) render high-resolution OpenGraph (`og:image`) preview cards for iMessage, Twitter, and social media.
- **Responsive & Accessible UI**: Lean, framework-free client interface with auto-detecting Light/Dark mode and player state persistence.

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

> **FreeBSD Note**: Install dependencies via `sudo pkg install py312-fastapi py312-pydantic py312-uvicorn py312-pillow py312-Jinja2 py312-markdown py312-mutagen py312-pyyaml py312-h2 py312-pytest py312-httpx py312-pytest-cov`, then initialize venv with `--system-site-packages`.

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
  "cache_dir": "./data/cache",
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

**lissn** maintains a comprehensive automated test suite (`pytest` + `pytest-cov`) covering API endpoints, RSS feed generation, HTTP range streaming, authentication, and file security restrictions.

### Run Test Suite & Generate Coverage Report
```bash
python3 -m pytest
```

### Coverage Metrics
```text
Name                    Stmts   Miss  Cover   Missing Lines
-----------------------------------------------------------
src/lissn/__init__.py       1      0   100%
src/lissn/app.py          355     34    90%   (error & fallback paths)
src/lissn/colors.py        83      5    94%   (invalid image fallbacks)
src/lissn/config.py        47      4    91%   (dir creation fallbacks)
src/lissn/rss.py           60      0   100%
src/lissn/scanner.py      324     31    90%   (corrupt tag fallbacks)
-----------------------------------------------------------
TOTAL                     870     74    91%
```

---

## 🔒 Production Deployment & Reverse Proxy

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
