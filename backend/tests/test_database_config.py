"""
Tests for app/database.py's configurable DB_PATH and ensure_database_ready().
Uses the same temp-database monkeypatch pattern as the other repository tests.
"""

import pytest

from app import database
from app.repositories import route_repository
from app.schemas import RouteScenario

SAMPLE_ROUTE = RouteScenario(
    id=1,
    city="Dallas",
    origin_label="Origin",
    destination_label="Destination",
    route_category="suburb_to_downtown",
    time_period="weekday_morning",
    distance_miles=10.0,
    driving_minutes=20,
    transit_minutes=40,
    walking_minutes=10,
    wait_transfer_minutes=10,
    transfers=0,
    fare_cost=3.0,
    gas_cost=3.0,
    driving_emissions_kg=5.0,
    transit_emissions_kg=1.0,
    notes="",
)


def test_repository_functions_use_the_configured_db_path(tmp_path, monkeypatch):
    custom_path = tmp_path / "custom.db"
    monkeypatch.setattr(database, "DB_PATH", custom_path)

    database.init_db()
    route_repository.replace_all_routes([SAMPLE_ROUTE])

    assert custom_path.exists()
    assert len(route_repository.list_routes()) == 1


def test_ensure_database_ready_fails_when_file_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "does-not-exist.db")

    with pytest.raises(RuntimeError, match="bootstrap_production"):
        database.ensure_database_ready()


def test_ensure_database_ready_fails_when_schema_missing(tmp_path, monkeypatch):
    empty_file = tmp_path / "empty.db"
    empty_file.touch()
    monkeypatch.setattr(database, "DB_PATH", empty_file)

    with pytest.raises(RuntimeError, match="not initialized"):
        database.ensure_database_ready()


def test_ensure_database_ready_fails_when_no_curated_scenarios(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "schema-only.db")
    database.init_db()

    with pytest.raises(RuntimeError, match="no curated scenarios"):
        database.ensure_database_ready()


def test_ensure_database_ready_passes_for_a_seeded_database(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "seeded.db")
    database.init_db()
    route_repository.replace_all_routes([SAMPLE_ROUTE])

    database.ensure_database_ready()  # should not raise
