"""
logging_config.py
=================
Centralized logging setup for the Local AI Assistant.

All modules should use get_logger() to obtain a logger instance:

    from utils.logging_config import get_logger
    logger = get_logger(__name__)
    logger.info("Something happened")
    logger.error("Something went wrong: %s", exc_text)

Log output:
  - File:  .local/logs/app.log (rotating, 5 MB max, 5 backups)
  - Console: WARNING and above (to avoid spamming the pywebview console)
  - Format: [HH:MM:SS] [LEVEL] module.name: message
"""

import logging
import os
from logging.handlers import RotatingFileHandler

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".local", "logs")
_LOG_FILE = os.path.join(_LOG_DIR, "app.log")
_MAX_BYTES = 5 * 1024 * 1024  # 5 MB
_BACKUP_COUNT = 5
_LOG_FORMAT = "[%(asctime)s] [%(levelname)-8s] %(name)s: %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

def setup_logging(level: int = logging.DEBUG) -> None:
    """
    Configure the root logger with file and console handlers.

    Call once at application startup (e.g. in run_web.py or app/main.py).
    Subsequent calls are no-ops.

    Args:
        level: Minimum log level (default: DEBUG).
    """
    root = logging.getLogger()

    # Avoid double-configuration if setup_logging is called more than once
    if root.handlers:
        return

    os.makedirs(_LOG_DIR, exist_ok=True)

    # File handler — detailed logs written to disk
    file_handler = RotatingFileHandler(
        _LOG_FILE,
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))

    # Console handler — only WARNING+ to avoid console spam
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))

    root.addHandler(file_handler)
    root.addHandler(console_handler)
    root.setLevel(level)


def get_logger(name: str) -> logging.Logger:
    """
    Get a named logger instance.

    Args:
        name: Logger name (typically ``__name__``).

    Returns:
        A configured logging.Logger instance.
    """
    return logging.getLogger(name)


# ---------------------------------------------------------------------------
# Convenience aliases — for modules that want to call logger.debug() etc.
# directly without assigning to a variable.
# ---------------------------------------------------------------------------

def debug(msg: str, *args, **kwargs) -> None:
    get_logger("local_ai").debug(msg, *args, **kwargs)


def info(msg: str, *args, **kwargs) -> None:
    get_logger("local_ai").info(msg, *args, **kwargs)


def warning(msg: str, *args, **kwargs) -> None:
    get_logger("local_ai").warning(msg, *args, **kwargs)


def error(msg: str, *args, **kwargs) -> None:
    get_logger("local_ai").error(msg, *args, **kwargs)


def critical(msg: str, *args, **kwargs) -> None:
    get_logger("local_ai").critical(msg, *args, **kwargs)
