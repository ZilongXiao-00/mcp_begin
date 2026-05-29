"""Unit tests for src/logger.py — Requirements 9.1, 9.5."""
import io
import logging
import re
import sys

import pytest

from src.logger import get_logger


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

LOG_LINE_RE = re.compile(
    r"^\[\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\] \[(DEBUG|INFO|WARNING|ERROR)\] .+$"
)


def _fresh_logger(name: str) -> logging.Logger:
    """Return a logger with no pre-existing handlers (isolated per test)."""
    logger = logging.getLogger(name)
    logger.handlers.clear()
    return get_logger(name)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_get_logger_returns_logger():
    logger = _fresh_logger("test.returns_logger")
    assert isinstance(logger, logging.Logger)


def test_get_logger_has_exactly_one_handler():
    logger = _fresh_logger("test.one_handler")
    assert len(logger.handlers) == 1


def test_get_logger_no_duplicate_handlers_on_repeated_calls():
    name = "test.no_duplicates"
    logging.getLogger(name).handlers.clear()
    get_logger(name)
    get_logger(name)
    get_logger(name)
    assert len(logging.getLogger(name).handlers) == 1


def test_get_logger_handler_is_stream_handler_to_stderr():
    logger = _fresh_logger("test.stderr_handler")
    handler = logger.handlers[0]
    assert isinstance(handler, logging.StreamHandler)
    assert handler.stream is sys.stderr


def test_get_logger_level_is_debug():
    logger = _fresh_logger("test.debug_level")
    assert logger.level == logging.DEBUG


def test_log_output_format_matches_iso8601():
    """Each emitted line must match [YYYY-MM-DDTHH:MM:SS] [LEVEL] message."""
    buf = io.StringIO()
    name = "test.format"
    logger = logging.getLogger(name)
    logger.handlers.clear()
    handler = logging.StreamHandler(buf)
    handler.setFormatter(
        logging.Formatter(
            fmt="[%(asctime)s] [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    )
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    logger.debug("debug message")
    logger.info("info message")
    logger.warning("warning message")
    logger.error("error message")

    lines = [l for l in buf.getvalue().splitlines() if l.strip()]
    assert len(lines) == 4
    for line in lines:
        assert LOG_LINE_RE.match(line), f"Line did not match expected format: {line!r}"


def test_log_output_goes_to_stderr_not_stdout(capsys):
    """Logging must not pollute stdout."""
    name = "test.stderr_only"
    logging.getLogger(name).handlers.clear()
    logger = get_logger(name)

    logger.info("hello stderr")

    captured = capsys.readouterr()
    assert captured.out == "", "Log output must not appear on stdout"
    assert "hello stderr" in captured.err
