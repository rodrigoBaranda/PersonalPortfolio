"""Utility logging configuration."""
from __future__ import annotations

import logging
import os
from typing import Optional

_DEFAULT_LOG_LEVEL = os.getenv("PORTFOLIO_LOG_LEVEL", "INFO").upper()
_LOGGER_INITIALIZED = False


def _configure_root_logger() -> None:
    """Configure the root logger once for the application."""
    global _LOGGER_INITIALIZED
    if _LOGGER_INITIALIZED:
        return

    level = getattr(logging, _DEFAULT_LOG_LEVEL, logging.INFO)

    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=level,
            format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        )
    else:
        logging.getLogger().setLevel(level)

    _LOGGER_INITIALIZED = True


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Return a logger with consistent configuration."""
    _configure_root_logger()
    return logging.getLogger(name if name else "portfolio")
