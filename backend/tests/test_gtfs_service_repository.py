"""
Tests for gtfs_service_repository.py, against a temporary SQLite file
seeded directly through gtfs_repository's insert_* functions.
"""

import pytest

from app import database
from app.repositories import gtfs_repository, gtfs_service_repository


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "test.db")
    database.init_db()


def test_get_route_found(temp_db):
    gtfs_repository.insert_routes([("CTA", "R1", "1", "1", "Red Line", "1")])

    route = gtfs_service_repository.get_route("CTA", "R1")

    assert route is not None
    assert route["route_long_name"] == "Red Line"


def test_get_route_agency_is_case_insensitive(temp_db):
    gtfs_repository.insert_routes([("CTA", "R1", "1", "1", "Red Line", "1")])

    assert gtfs_service_repository.get_route("cta", "R1") is not None


def test_get_route_route_id_is_case_sensitive(temp_db):
    # route_id is an opaque GTFS identifier, not fuzzy-matched like agency_source.
    gtfs_repository.insert_routes([("CTA", "R1", "1", "1", "Red Line", "1")])

    assert gtfs_service_repository.get_route("CTA", "r1") is None


def test_get_route_unknown_returns_none(temp_db):
    assert gtfs_service_repository.get_route("CTA", "NOPE") is None
    assert gtfs_service_repository.get_route("NOPE", "R1") is None


def test_get_first_stop_departure_times_filters_by_stop_sequence(temp_db):
    gtfs_repository.insert_trips([("CTA", "T1", "R1", "WD", "Downtown", "0")])
    gtfs_repository.insert_stop_times(
        [
            ("CTA", "T1", "S1", "08:00:00", "08:00:00", 1),
            ("CTA", "T1", "S2", "08:05:00", "08:05:00", 2),  # ignored: not stop_sequence 1
        ]
    )

    times = gtfs_service_repository.get_first_stop_departure_times("CTA", "R1", ["WD"])

    assert times == ["08:00:00"]


def test_get_first_stop_departure_times_filters_by_active_service_ids(temp_db):
    gtfs_repository.insert_trips(
        [
            ("CTA", "T1", "R1", "WD", "Downtown", "0"),
            ("CTA", "T2", "R1", "SAT", "Downtown", "0"),
        ]
    )
    gtfs_repository.insert_stop_times(
        [
            ("CTA", "T1", "S1", "08:00:00", "08:00:00", 1),
            ("CTA", "T2", "S1", "10:00:00", "10:00:00", 1),
        ]
    )

    # Only the "WD" trip's departure should come back when only "WD" is active.
    assert gtfs_service_repository.get_first_stop_departure_times("CTA", "R1", ["WD"]) == ["08:00:00"]
    assert gtfs_service_repository.get_first_stop_departure_times("CTA", "R1", ["SAT"]) == ["10:00:00"]
    assert gtfs_service_repository.get_first_stop_departure_times("CTA", "R1", []) == []


def test_get_first_stop_departure_times_for_unknown_route_returns_empty_list(temp_db):
    assert gtfs_service_repository.get_first_stop_departure_times("CTA", "NOPE", ["WD"]) == []


def test_same_route_id_across_agencies_does_not_mix(temp_db):
    gtfs_repository.insert_routes(
        [
            ("CTA", "R1", "1", "1", "CTA Red Line", "1"),
            ("DART", "R1", "1", "1", "DART Red Line", "2"),
        ]
    )
    # Same trip_id ("T1") and service_id ("WD") reused by both agencies on
    # purpose -- both are only guaranteed unique within one agency's feed.
    gtfs_repository.insert_trips(
        [
            ("CTA", "T1", "R1", "WD", "Downtown", "0"),
            ("DART", "T1", "R1", "WD", "Downtown", "0"),
        ]
    )
    gtfs_repository.insert_stop_times(
        [
            ("CTA", "T1", "S1", "08:00:00", "08:00:00", 1),
            ("DART", "T1", "S1", "09:00:00", "09:00:00", 1),
        ]
    )

    cta_route = gtfs_service_repository.get_route("CTA", "R1")
    dart_route = gtfs_service_repository.get_route("DART", "R1")
    assert cta_route["route_long_name"] == "CTA Red Line"
    assert dart_route["route_long_name"] == "DART Red Line"

    assert gtfs_service_repository.get_first_stop_departure_times("CTA", "R1", ["WD"]) == ["08:00:00"]
    assert gtfs_service_repository.get_first_stop_departure_times("DART", "R1", ["WD"]) == ["09:00:00"]


def test_get_agency_timezone_found(temp_db):
    gtfs_repository.insert_agencies([("CTA", "1", "Test CTA", "http://cta.example", "America/Chicago")])

    assert gtfs_service_repository.get_agency_timezone("CTA") == "America/Chicago"


def test_get_agency_timezone_is_case_insensitive(temp_db):
    gtfs_repository.insert_agencies([("CTA", "1", "Test CTA", "http://cta.example", "America/Chicago")])

    assert gtfs_service_repository.get_agency_timezone("cta") == "America/Chicago"


def test_get_agency_timezone_unknown_returns_none(temp_db):
    assert gtfs_service_repository.get_agency_timezone("NOPE") is None


def test_get_calendar_service_ids_for_weekday_matches_date_range_and_weekday(temp_db):
    gtfs_repository.insert_calendar(
        [("CTA", "WD", 1, 1, 1, 1, 1, 0, 0, "20260101", "20261231")]
    )

    # 2026-08-11 is a Tuesday; "tuesday" column is 1 for "WD".
    assert gtfs_service_repository.get_calendar_service_ids_for_weekday("CTA", "tuesday", "20260811") == ["WD"]
    # "WD" doesn't run Saturdays.
    assert gtfs_service_repository.get_calendar_service_ids_for_weekday("CTA", "saturday", "20260811") == []
    # Outside the service date range entirely.
    assert gtfs_service_repository.get_calendar_service_ids_for_weekday("CTA", "tuesday", "20270101") == []


def test_get_calendar_service_ids_for_weekday_differs_by_service_pattern(temp_db):
    gtfs_repository.insert_calendar(
        [
            ("CTA", "WD", 1, 1, 1, 1, 1, 0, 0, "20260101", "20261231"),
            ("CTA", "SAT", 0, 0, 0, 0, 0, 1, 0, "20260101", "20261231"),
        ]
    )

    assert gtfs_service_repository.get_calendar_service_ids_for_weekday("CTA", "tuesday", "20260811") == ["WD"]
    assert gtfs_service_repository.get_calendar_service_ids_for_weekday("CTA", "saturday", "20260815") == ["SAT"]


def test_get_calendar_date_exceptions_returns_pairs_for_exact_date(temp_db):
    gtfs_repository.insert_calendar_dates(
        [
            ("CTA", "HOLIDAY", "20260704", "1"),
            ("CTA", "WD", "20260704", "2"),
        ]
    )

    exceptions = gtfs_service_repository.get_calendar_date_exceptions("CTA", "20260704")

    assert set(exceptions) == {("HOLIDAY", "1"), ("WD", "2")}
    assert gtfs_service_repository.get_calendar_date_exceptions("CTA", "20260705") == []
