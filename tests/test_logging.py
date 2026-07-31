"""
Unit tests for logging configuration in lissn.app.
Verifies that file handlers correctly create log files and write log records.
"""

from pathlib import Path
import logging
import pytest

from lissn.config import Config
from lissn.app import configure_logging


def test_configure_logging(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test configure_logging attaches file handler and writes logs to specified file."""
    log_dir = tmp_path / "logs"
    log_file = log_dir / "lissn.log"

    config = Config(log_dir=str(log_dir), log_file_path=str(log_file))

    # Reset any existing lissn logger handlers for isolation
    logger = logging.getLogger("lissn")
    logger.handlers.clear()

    configured_logger = configure_logging(config)

    assert log_file.parent.is_dir()
    
    test_message = "Test log entry for service logging verification"
    configured_logger.info(test_message)

    # Flush handlers to ensure file content is written
    for handler in configured_logger.handlers:
        handler.flush()

    assert log_file.exists()
    content = log_file.read_text(encoding="utf-8")
    assert test_message in content


def test_configure_logging_verbose_level(tmp_path: Path) -> None:
    """Test configure_logging sets DEBUG level when verbose mode is enabled."""
    log_dir = tmp_path / "logs"
    log_file = log_dir / "lissn_debug.log"

    config = Config(log_dir=str(log_dir), log_file_path=str(log_file), verbose=True)

    logger = logging.getLogger("lissn")
    logger.handlers.clear()

    configured_logger = configure_logging(config)

    debug_msg = "Verbose debug output test string"
    configured_logger.debug(debug_msg)

    for handler in configured_logger.handlers:
        handler.flush()

    assert log_file.exists()
    content = log_file.read_text(encoding="utf-8")
    assert debug_msg in content


def test_extract_client_ips_x_forwarded_for() -> None:
    """Test extract_client_ips correctly parses first IP in X-Forwarded-For header."""
    from fastapi import Request
    from lissn.app import extract_client_ips

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [(b"x-forwarded-for", b"203.0.113.195, 10.0.0.1")],
        "client": ("127.0.0.1", 50000),
    }
    request = Request(scope)
    real_ip, proxy_ip = extract_client_ips(request)

    assert real_ip == "203.0.113.195"
    assert proxy_ip == "127.0.0.1"


def test_extract_client_ips_x_real_ip() -> None:
    """Test extract_client_ips correctly falls back to X-Real-IP header."""
    from fastapi import Request
    from lissn.app import extract_client_ips

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [(b"x-real-ip", b"198.51.100.4")],
        "client": ("127.0.0.1", 50000),
    }
    request = Request(scope)
    real_ip, proxy_ip = extract_client_ips(request)

    assert real_ip == "198.51.100.4"
    assert proxy_ip == "127.0.0.1"


def test_extract_client_ips_direct_connection() -> None:
    """Test extract_client_ips returns client IP when no proxy headers are present."""
    from fastapi import Request
    from lissn.app import extract_client_ips

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [],
        "client": ("192.168.1.100", 50000),
    }
    request = Request(scope)
    real_ip, proxy_ip = extract_client_ips(request)

    assert real_ip == "192.168.1.100"
    assert proxy_ip == "192.168.1.100"


def test_request_logging_middleware(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test request logging middleware logs requests with real IP and proxy IP format."""
    from fastapi.testclient import TestClient
    from lissn.app import app, configure_logging, logger as app_logger

    log_dir = tmp_path / "logs"
    log_file = log_dir / "lissn_requests.log"
    config = Config(log_dir=str(log_dir), log_file_path=str(log_file))

    app_logger.handlers.clear()
    configured_logger = configure_logging(config)

    client = TestClient(app)
    headers = {"X-Forwarded-For": "203.0.113.195"}
    response = client.get("/static/style.css", headers=headers)

    assert response.status_code == 200

    for handler in configured_logger.handlers:
        handler.flush()

    assert log_file.exists()
    log_content = log_file.read_text(encoding="utf-8")
    assert "203.0.113.195 (via proxy" in log_content
    assert '"GET /static/style.css" 200' in log_content


