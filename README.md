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

- **Folder Indexing**: Automatically scans configurable directories for **Audio Books** (`.../Books`) and **Podcasts** (`.../Podcasts`).
- **Show Duration & Fuzzy Dates**: Calculates total audio duration across `.mp3`, `.m4a`, `.m4b`, `.aac`, `.flac`, `.ogg`, `.opus`, and `.wav` files, and formats fuzzy added timestamps (*e.g., "3 days ago"*).
- **Per-Show `notes.md` Metadata**: Auto-generates a `notes.md` file inside `cache/books/<show_name>/` or `cache/podcasts/<show_name>/` allowing custom `title`, `author`, `podcast_name`, and rich Markdown descriptions.
- **Podcast RSS 2.0 Feeds**: Generates valid iTunes-compatible podcast XML feeds for 1-click subscription in podcast apps (`podcast://` protocol) or direct RSS feed link copying.
- **iMessage & Instagram Social Share Cards**: Dedicated show pages (`/show/{show_id}`) include OpenGraph (`og:image`, `og:title`, `og:description`) and Twitter Card tags to render high-resolution cover image preview cards when shared.
- **Responsive & Accessible UI**: Clean, framework-free interface supporting system preference and manual Light/Dark mode switching.

---

## 🚀 Quick Start & Installation

### Prerequisites
- **Python 3.10+** (tested on FreeBSD, Linux, and macOS)

### 1. Clone Repository
```bash
git clone https://github.com/jakobbg/lissn.git
cd lissn
```

### 2. Create & Activate Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

#### Standard Installation (Linux & macOS)
```bash
pip install -e .
```

#### FreeBSD Installation Notes
On FreeBSD, Python packages with native Rust extensions (such as `pydantic-core`) do not have pre-built wheel binaries on PyPI. Choose one of the following setup options:

##### Method 1: FreeBSD Binary Packages (Recommended)
Use FreeBSD `pkg` to install pre-compiled binaries, then enable `--system-site-packages` in your virtual environment:

```bash
# Install pre-compiled binary packages
sudo pkg install py312-fastapi py312-pydantic py312-uvicorn py312-pillow py312-Jinja2 py312-markdown py312-mutagen py312-pyyaml py312-h2 py312-pytest py312-httpx py312-python-multipart

# Create venv with system site packages enabled
python3 -m venv --system-site-packages .venv
source .venv/bin/activate

# Install lissn package
pip install --no-deps -e .
```

##### Method 2: Install Rust Compiler
Alternatively, install the Rust compiler so `pip` can build Rust extensions from source:

```bash
# Install Rust toolchain via pkg
sudo pkg install rust

# Standard pip install in venv
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 4. Create Configuration File
Copy the example configuration file to `config/lissn.json`:
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

### 5. Start Application
```bash
python3 -m lissn.app
```

Open your browser and navigate to `http://localhost:8000`.

---

## 🔒 HTTPS & Reverse Proxy Deployment

For security, performance, and compatibility with modern web features (such as background audio playback and automated SSL certificates), **lissn** should be hosted behind a **Reverse Proxy** handling TLS/HTTPS termination in production environments.

### Option 1: Caddy (Recommended - Automatic HTTPS)
[Caddy](https://caddyserver.com/) automatically obtains, configures, and renews free SSL certificates via Let's Encrypt / ZeroSSL.

Example `Caddyfile`:
```caddyfile
lissn.example.com {
    reverse_proxy localhost:8000
}
```

Update `base_url` in your `config/lissn.json` to match your domain:
```json
{
  "base_url": "https://lissn.example.com"
}
```

### Option 2: Tailscale Serve (Private Network / Tailnet HTTPS)
If accessing **lissn** over [Tailscale](https://tailscale.com/), enable instant HTTPS on your private network:
```bash
tailscale serve https / http://localhost:8000
```

### Option 3: Nginx
Example Nginx server block with HTTP/2 and web socket/streaming support:
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

### Option 4: Apache HTTP Server (`mod_proxy`)
Example Apache VirtualHost configuration requiring `mod_proxy`, `mod_proxy_http`, `mod_ssl`, and `mod_headers`:

```apache
<VirtualHost *:443>
    ServerName lissn.example.com

    SSLEngine on
    SSLCertificateFile /etc/letsencrypt/live/lissn.example.com/fullchain.pem
    SSLCertificateKeyFile /etc/letsencrypt/live/lissn.example.com/privkey.pem

    Protocols h2 http/1.1

    # Preserve host and pass client headers
    ProxyPreserveHost On
    RequestHeader set X-Forwarded-Proto "https"

    # Reverse proxy setup
    ProxyPass / http://127.0.0.1:8000/
    ProxyPassReverse / http://127.0.0.1:8000/
</VirtualHost>
```

> **Note:** Ensure required modules are enabled:
> - **Debian / Ubuntu**: `sudo a2enmod proxy proxy_http ssl headers http2 && sudo systemctl restart apache2`
> - **FreeBSD**: Enable `mod_proxy`, `mod_proxy_http`, `mod_ssl`, `mod_headers`, and `mod_http2` in `/usr/local/etc/apache24/httpd.conf`.

---

## 🧪 Running Automated Tests

Run the test suite using `python3 -m pytest` within your activated environment:

```bash
python3 -m pytest
```

If you are using FreeBSD `pkg` packages, make sure `py312-pytest` and `py312-httpx` are installed:
```bash
sudo pkg install py312-pytest py312-httpx
```

## 🛠️ Local Development & IDE Debugging

### 1. Seed Sample Media Library (No real files required)
Populate `./data/Books` and `./data/Podcasts` with dummy audio files and cover art for instant local testing without needing to download external files:
```bash
python scripts/seed_dev_data.py
```

### 2. IDE Integration (VS Code / Cursor)
The repository includes `.vscode/launch.json` pre-configured for **Run & Debug** (`F5`):
- **`lissn: Run & Debug Web Server`**: Launches the web server with live debugging and breakpoints at `http://localhost:8000`.
- **`lissn: Seed Dev Media Library`**: Runs the sample data generator script.
- **`pytest: Debug All Tests`**: Debugs the pytest automated test suite.
- **`pytest: Debug Current Test File`**: Debugs the test file currently active in your editor.

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for details.

