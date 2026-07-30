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

