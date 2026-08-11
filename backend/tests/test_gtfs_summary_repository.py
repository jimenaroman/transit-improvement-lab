"""
Tests for gtfs_summary_repository.py.

Uses the same temp-database pattern as the other repository tests, seeded
directly through gtfs_repository's insert_* functions rather than a real
GTFS zip, so these stay fast and focused on the summary/query logic itself.
"""

import pytest

from app import database
from app.repositories import gtfs_repository, gtfs_summary_repository


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "test.db")
    database.init_db()


def test_get_summary_counts_per_agency(temp_db):
    gtfs_repository.insert_agencies([("CTA", "1", "Test CTA", "http://cta.example", "America/Chicago")])
    gtfs_repository.insert_routes([("CTA", "R1", "1", "Red", "Red Line", "1")])
    gtfs_repository.insert_stops([("CTA", "S1", "Stop One", 41.8, -87.6)])
    gtfs_repository.insert_trips([("CTA", "T1", "R1", "WD", "Downtown", "0")])
    gtfs_repository.insert_stop_times([("CTA", "T1", "S1", "08:00:00", "08:00:00", 1)])
    gtfs_repository.insert_calendar([("CTA", "WD", 1, 1, 1, 1, 1, 0, 0, "20260101", "20261231")])
    gtfs_repository.insert_calendar_dates([("CTA", "WD", "20260704", "2")])

    summary = gtfs_summary_repository.get_summary()

    assert len(summary) == 1
    cta = summary[0]
    assert cta.agency_source == "CTA"
    assert cta.routes == 1
    assert cta.stops == 1
    assert cta.trips == 1
    assert cta.stop_times == 1
    assert cta.calendar == 1
    assert cta.calendar_dates == 1


def test_get_summary_returns_empty_list_when_no_data(temp_db):
    assert gtfs_summary_repository.get_summary() == []


def test_get_summary_includes_partially_imported_agency(temp_db):
    # Only routes imported for this agency so far — should still appear,
    # with 0s for the tables that haven't been loaded yet.
    gtfs_repository.insert_routes([("DART", "R1", "1", "1", "Blue Line", "1")])

    summary = gtfs_summary_repository.get_summary()

    dart = next(row for row in summary if row.agency_source == "DART")
    assert dart.routes == 1
    assert dart.stops == 0
    assert dart.trips == 0


def test_get_routes_for_agency_includes_zero_trip_routes(temp_db):
    gtfs_repository.insert_routes(
        [
            ("CTA", "R1", "1", "1", "Red Line", "1"),
            ("CTA", "R2", "1", "2", "Blue Line", "1"),
        ]
    )
    gtfs_repository.insert_trips(
        [
            ("CTA", "T1", "R1", "WD", "Downtown", "0"),
            ("CTA", "T2", "R1", "WD", "Downtown", "0"),
        ]
    )

    routes = gtfs_summary_repository.get_routes_for_agency("CTA")

    by_id = {route.route_id: route for route in routes}
    assert by_id["R1"].trip_count == 2
    assert by_id["R2"].trip_count == 0


def test_get_routes_for_agency_is_case_insensitive(temp_db):
    gtfs_repository.insert_routes([("CTA", "R1", "1", "1", "Red Line", "1")])

    assert len(gtfs_summary_repository.get_routes_for_agency("cta")) == 1


def test_get_routes_for_unknown_agency_returns_empty_list(temp_db):
    gtfs_repository.insert_routes([("CTA", "R1", "1", "1", "Red Line", "1")])

    assert gtfs_summary_repository.get_routes_for_agency("DART") == []


def test_get_top_routes_by_trips_orders_and_limits(temp_db):
    gtfs_repository.insert_routes(
        [
            ("CTA", "R1", "1", "1", "Red Line", "1"),
            ("CTA", "R2", "1", "2", "Blue Line", "1"),
            ("CTA", "R3", "1", "3", "Green Line", "1"),
        ]
    )
    gtfs_repository.insert_trips(
        [
            ("CTA", "T1", "R1", "WD", "Downtown", "0"),
            ("CTA", "T2", "R2", "WD", "Downtown", "0"),
            ("CTA", "T3", "R2", "WD", "Downtown", "0"),
            ("CTA", "T4", "R2", "WD", "Downtown", "0"),
        ]
    )

    top = gtfs_summary_repository.get_top_routes_by_trips("CTA", limit=2)

    assert [route.route_id for route in top] == ["R2", "R1"]
