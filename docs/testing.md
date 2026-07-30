# Testing & Code Quality Guide

This document details the automated test suite, coverage reporting, and code quality workflows for **lissn**.

---

## 🧪 Running the Test Suite

**lissn** uses `pytest` for all unit and integration testing.

### 1. Prerequisites
Ensure dev dependencies are installed inside your virtual environment:

```bash
pip install -e ".[dev]"
```

> **FreeBSD System Packages**: On FreeBSD, you can also install test runner packages via `pkg`:
> ```bash
> sudo pkg install py312-pytest py312-httpx py312-pytest-cov
> ```

### 2. Execute Tests
Run all automated tests from the project root:

```bash
python3 -m pytest
```

---

## 📊 Code Coverage Reports

Coverage reports are managed via `pytest-cov`.

### Run Tests with Coverage Report
```bash
python3 -m pytest --cov=lissn --cov-report=term-missing
```

### Coverage Targets & Metrics
The codebase aims to maintain ≥ 90% overall line coverage across key modules:

| Module | Purpose | Target Coverage |
| :--- | :--- | :--- |
| `src/lissn/app.py` | FastAPI routes, RSS endpoints & HTTP audio streaming | ≥ 85% |
| `src/lissn/scanner.py` | Media library indexing, SQLite caching & tag parsing | ≥ 90% |
| `src/lissn/colors.py` | Dynamic palette extractions & gradient fallbacks | ≥ 90% |
| `src/lissn/config.py` | JSON configuration & environment variable overrides | ≥ 90% |
| `src/lissn/rss.py` | iTunes RSS 2.0 XML generator | ≥ 95% |
| `src/lissn/version.py` | Git metadata extraction & app versioning | ≥ 90% |

---

## 📁 Test Suite Structure

All test cases are located in the `tests/` directory:

```text
tests/
├── conftest.py           # Shared pytest fixtures (temporary media dirs, test SQLite DB)
├── test_app.py           # Web application endpoints, authentication & ZIP streaming
├── test_colors.py        # Dominant color extraction & image processing tests
├── test_config.py        # Configuration loading, environment variables & logging settings
├── test_rss.py           # RSS 2.0 feed generator & iTunes podcast tags validation
├── test_scanner.py       # Folder scanning, audio tag parsing & database caching
└── test_version.py       # Version resolution & Git fallback logic
```

---

## ✍️ Writing New Tests

When adding features or bug fixes:

1. Place new test functions in `tests/test_<module_name>.py`.
2. Use standard `pytest` fixtures defined in `tests/conftest.py` (such as `tmp_path` or synthetic media generators).
3. Ensure user input sanitization and HTTP status code fallbacks are explicitly asserted.
