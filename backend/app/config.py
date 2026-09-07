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


def get_database_path() -> Path:
    """DATABASE_PATH if set (production), else the same local dev path used before this existed."""
    configured = os.getenv("DATABASE_PATH")
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[1] / "transit_lab.db"


def get_cta_gtfs_zip_path() -> Path | None:
    """Local path to a CTA static GTFS zip for bootstrap, or None if unset."""
    configured = os.getenv("GTFS_CTA_ZIP_PATH")
    return Path(configured) if configured else None


def get_dart_gtfs_zip_path() -> Path | None:
    """Local path to a DART static GTFS zip for bootstrap, or None if unset."""
    configured = os.getenv("GTFS_DART_ZIP_PATH")
    return Path(configured) if configured else None
