# lissn 🎧

**lissn** is a Python-based web application and RSS feed generator designed to index, serve, and share your personal **Audio Books** and **Podcasts**.

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
```bash
pip install -e .
```

### 4. Create Configuration File
Copy the example configuration file to `lissn.json`:
```bash
cp config/lissn.example.json lissn.json
```

Edit `lissn.json` to point to your media directories:
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

## 🧪 Running Automated Tests

Run the test suite using `pytest`:
```bash
pytest
```

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for details.
