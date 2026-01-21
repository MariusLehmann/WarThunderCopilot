"""Central logging helper for the project.

Provides `get_logger(name, filename=None, level=None)` which ensures the
central configuration from `code.settings` is applied and optionally adds a
per-module rotating file handler in the project's `logs/` directory.
"""
from __future__ import annotations

import logging
import logging.handlers
from typing import Optional
from pathlib import Path

import settings

_configured = False


def _ensure_configured() -> None:
    global _configured
    if _configured:
        return
    try:
        settings.configure_logging()
    except Exception:
        # If central config fails, fall back to a minimal configuration
        logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL))
    _configured = True


def _handler_already_attached(logger: logging.Logger, filename: str) -> bool:
    for h in logger.handlers:
        base = getattr(h, 'baseFilename', None)
        if base and Path(base).name == Path(filename).name:
            return True
    return False


def get_logger(name: str, *, filename: Optional[str] = None, level: Optional[int] = None) -> logging.Logger:
    """Return a configured logger for `name`.

    If `filename` is provided, attach a RotatingFileHandler that writes to
    `settings.LOG_DIR / filename`. Duplicate handlers are avoided.

    `level` can be an int (e.g. logging.DEBUG) to override the logger level.
    """
    _ensure_configured()
    logger = logging.getLogger(name)

    if level is not None:
        logger.setLevel(level)

    if filename:
        try:
            log_dir = Path(settings.LOG_DIR)
            log_dir.mkdir(parents=True, exist_ok=True)
            filepath = log_dir / filename
            if not _handler_already_attached(logger, str(filepath)):
                handler = logging.handlers.RotatingFileHandler(
                    filename=str(filepath), mode='a', maxBytes=10 * 1024 * 1024, backupCount=3, encoding='utf-8'
                )
                formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                handler.setFormatter(formatter)
                handler.setLevel(getattr(logging, settings.LOG_LEVEL))
                logger.addHandler(handler)
        except Exception:
            # If per-module file handler cannot be created, ignore and continue
            pass

    return logger
