"""Application configuration helpers.

This module centralizes workbook/worksheet configuration so that the Google
Sheets workbook name can be overridden without editing the code. The worksheet
name intentionally remains fixed to ``"Transactions"`` because the rest of the
application expects the tab to use that name.

Priority order for the workbook name:

1. ``st.secrets["workbook_name"]`` if running inside Streamlit with a
   ``.streamlit/secrets.toml`` file.
2. ``PORTFOLIO_WORKBOOK_NAME`` environment variable.
3. The JSON file ``config/workbook.json`` (``{"workbook_name": "..."}``).
4. Fallback to ``"Transactions"``.

The helper functions are intentionally small and dependency-free so they work
both in the Streamlit runtime and when running unit tests.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Optional


DEFAULT_WORKBOOK_NAME = "Transactions"
WORKSHEET_NAME = "Transactions"

# Environment variable that can be exported to set the workbook name.
WORKBOOK_ENV_VAR = "PORTFOLIO_WORKBOOK_NAME"

# Optional JSON configuration file relative to the project root. The JSON must
# contain a single key called ``workbook_name``.
WORKBOOK_JSON_PATH = Path("config/workbook.json")


def _read_workbook_from_streamlit() -> Optional[str]:
    """Attempt to read the workbook name from ``st.secrets``.

    Returns ``None`` if Streamlit is not installed or when the key is missing.
    """

    try:  # Streamlit may not be available during unit tests.
        import streamlit as st  # type: ignore
    except ModuleNotFoundError:
        return None

    secrets = getattr(st, "secrets", None)
    if secrets is None:
        return None

    try:
        value = secrets.get("workbook_name")
    except Exception:
        # Accessing st.secrets can raise a RuntimeError if not initialised yet.
        return None

    if isinstance(value, str) and value.strip():
        return value.strip()

    return None


def _read_workbook_from_env() -> Optional[str]:
    """Return the workbook name from the environment variable if available."""

    value = os.getenv(WORKBOOK_ENV_VAR, "").strip()
    return value or None


def _read_workbook_from_json() -> Optional[str]:
    """Return the workbook name from ``config/workbook.json`` if present."""

    if not WORKBOOK_JSON_PATH.exists():
        return None

    try:
        payload = json.loads(WORKBOOK_JSON_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    value = payload.get("workbook_name") if isinstance(payload, dict) else None
    if isinstance(value, str) and value.strip():
        return value.strip()

    return None


@lru_cache(maxsize=1)
def get_workbook_name() -> str:
    """Resolve the Google Sheets workbook name."""

    return (
        _read_workbook_from_streamlit()
        or _read_workbook_from_env()
        or _read_workbook_from_json()
        or DEFAULT_WORKBOOK_NAME
    )


# Expose convenient module-level constants for imports elsewhere.
WORKBOOK_NAME = get_workbook_name()

