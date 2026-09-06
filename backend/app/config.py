"""
Environment variable loading for secrets/config. See docs/architecture.md.

Loads backend/.env once at import time. Never log a value read from here --
get_google_maps_api_key() exists so callers never touch os.environ directly
and can't accidentally print or interpolate a raw key into a log line.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


def get_google_maps_api_key() -> str | None:
    """Returns the configured key, or None if unset -- callers decide how to handle that."""
    return os.getenv("GOOGLE_MAPS_API_KEY")
