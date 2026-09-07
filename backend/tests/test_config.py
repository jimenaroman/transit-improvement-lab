"""
Tests for the production-config getters in app/config.py: DATABASE_PATH and
the two GTFS zip path env vars.
"""

from pathlib import Path

from app import config


def test_get_database_path_uses_env_var_when_set(monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", "/var/data/transit_lab.db")

    assert config.get_database_path() == Path("/var/data/transit_lab.db")


def test_get_database_path_falls_back_to_local_default(monkeypatch):
    monkeypatch.delenv("DATABASE_PATH", raising=False)

    path = config.get_database_path()

    assert path.name == "transit_lab.db"
    assert path.parent.name == "backend"


def test_get_cta_gtfs_zip_path_is_none_when_unset(monkeypatch):
    monkeypatch.delenv("GTFS_CTA_ZIP_PATH", raising=False)

    assert config.get_cta_gtfs_zip_path() is None


def test_get_cta_gtfs_zip_path_uses_env_var_when_set(monkeypatch):
    monkeypatch.setenv("GTFS_CTA_ZIP_PATH", "/var/data/gtfs/cta.zip")

    assert config.get_cta_gtfs_zip_path() == Path("/var/data/gtfs/cta.zip")


def test_get_dart_gtfs_zip_path_is_none_when_unset(monkeypatch):
    monkeypatch.delenv("GTFS_DART_ZIP_PATH", raising=False)

    assert config.get_dart_gtfs_zip_path() is None


def test_get_dart_gtfs_zip_path_uses_env_var_when_set(monkeypatch):
    monkeypatch.setenv("GTFS_DART_ZIP_PATH", "/var/data/gtfs/dart.zip")

    assert config.get_dart_gtfs_zip_path() == Path("/var/data/gtfs/dart.zip")
