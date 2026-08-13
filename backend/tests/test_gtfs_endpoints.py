"""
Tests for the /api/gtfs/... HTTP endpoints, using FastAPI's TestClient.

Repository logic itself is covered in test_gtfs_summary_repository.py —
these tests check the HTTP layer on top of it: status codes, URL routing,
query parameter handling, and JSON shape.
"""

import pytest
from fastapi.testclient import TestClient

from app import database
from app.main import app
from app.repositories import gtfs_repository

client = TestClient(app)


@pytest.fixture
def seeded_gtfs(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "test.db")
    database.init_db()
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
            ("CTA", "T3", "R2", "WD", "O'Hare", "0"),
        ]
    )


def test_summary_endpoint_returns_counts(seeded_gtfs):
    response = client.get("/api/gtfs/summary")

    assert response.status_code == 200
    body = response.json()
    cta = next(item for item in body if item["agency_source"] == "CTA")
    assert cta["routes"] == 2
    assert cta["trips"] == 3


def test_summary_endpoint_empty_database_returns_empty_list(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "empty.db")
    database.init_db()

    response = client.get("/api/gtfs/summary")

    assert response.status_code == 200
    assert response.json() == []


def test_agency_routes_endpoint_returns_trip_counts(seeded_gtfs):
    response = client.get("/api/gtfs/agencies/CTA/routes")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    r1 = next(item for item in body if item["route_id"] == "R1")
    assert r1["trip_count"] == 2
    assert r1["route_long_name"] == "Red Line"


def test_agency_routes_endpoint_is_case_insensitive(seeded_gtfs):
    response = client.get("/api/gtfs/agencies/cta/routes")

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_unknown_agency_returns_200_and_empty_list(seeded_gtfs):
    response = client.get("/api/gtfs/agencies/UNKNOWN/routes")

    assert response.status_code == 200
    assert response.json() == []


def test_top_routes_by_trips_orders_and_respects_limit(seeded_gtfs):
    response = client.get("/api/gtfs/agencies/CTA/top-routes-by-trips?limit=1")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["route_id"] == "R1"  # 2 trips vs. R2's 1


def test_top_routes_by_trips_uses_default_limit(seeded_gtfs):
    response = client.get("/api/gtfs/agencies/CTA/top-routes-by-trips")

    assert response.status_code == 200
    assert len(response.json()) == 2  # only 2 routes exist, default limit is 10


def test_top_routes_by_trips_rejects_limit_over_100(seeded_gtfs):
    response = client.get("/api/gtfs/agencies/CTA/top-routes-by-trips?limit=101")

    assert response.status_code == 422


@pytest.fixture
def seeded_gtfs_with_departures(tmp_path, monkeypatch):
    """
    "WD" is active every single day of the week (all seven calendar
    columns are 1) so that tests calling the endpoint without ?date=
    behave the same no matter what real-world day the test suite happens
    to run on. Tests that care about a specific weekday use a dedicated
    fixture below instead.
    """
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "svc.db")
    database.init_db()
    gtfs_repository.insert_routes([("CTA", "R1", "1", "1", "Red Line", "1")])
    gtfs_repository.insert_calendar([("CTA", "WD", 1, 1, 1, 1, 1, 1, 1, "20200101", "20301231")])
    gtfs_repository.insert_trips(
        [
            ("CTA", "T1", "R1", "WD", "Downtown", "0"),
            ("CTA", "T2", "R1", "WD", "Downtown", "0"),
        ]
    )
    gtfs_repository.insert_stop_times(
        [
            ("CTA", "T1", "S1", "08:00:00", "08:00:00", 1),
            ("CTA", "T2", "S1", "08:15:00", "08:15:00", 1),
        ]
    )


def test_service_summary_returns_200_with_calculated_fields(seeded_gtfs_with_departures):
    response = client.get("/api/gtfs/agencies/CTA/routes/R1/service-summary?date=2026-08-11")

    assert response.status_code == 200
    body = response.json()
    assert body["route_id"] == "R1"
    assert body["route_long_name"] == "Red Line"
    assert body["service_date"] == "2026-08-11"
    assert body["day_of_week"] == "Tuesday"
    assert body["active_service_ids"] == ["WD"]
    assert body["trip_count"] == 2
    assert body["first_departure_time"] == "08:00:00"
    assert body["last_departure_time"] == "08:15:00"
    assert body["average_headway_minutes"] == 15.0
    assert body["peak_headway_minutes"] == 15.0
    assert body["midday_headway_minutes"] is None
    assert body["evening_headway_minutes"] is None
    assert body["service_span_hours"] == 0.2  # 08:00 to 08:15 (0.25 hr, rounded to 1 decimal place)
    assert body["frequency_classification"] == "frequent"


def test_service_summary_unknown_route_returns_404(seeded_gtfs_with_departures):
    response = client.get("/api/gtfs/agencies/CTA/routes/NOPE/service-summary")

    assert response.status_code == 404


def test_service_summary_unknown_agency_returns_404(seeded_gtfs_with_departures):
    response = client.get("/api/gtfs/agencies/UNKNOWN/routes/R1/service-summary")

    assert response.status_code == 404


def test_service_summary_agency_is_case_insensitive(seeded_gtfs_with_departures):
    response = client.get("/api/gtfs/agencies/cta/routes/R1/service-summary")

    assert response.status_code == 200
    assert response.json()["agency_source"] == "CTA"


def test_service_summary_explicit_date_is_used(seeded_gtfs_with_departures):
    response = client.get("/api/gtfs/agencies/CTA/routes/R1/service-summary?date=2026-08-11")

    assert response.status_code == 200
    assert response.json()["service_date"] == "2026-08-11"


def test_service_summary_defaults_to_today_when_date_omitted(seeded_gtfs_with_departures):
    from datetime import datetime
    from zoneinfo import ZoneInfo

    response = client.get("/api/gtfs/agencies/CTA/routes/R1/service-summary")

    assert response.status_code == 200
    # No gtfs_agencies row is seeded, so this falls back to America/Chicago.
    expected_today = datetime.now(ZoneInfo("America/Chicago")).date().isoformat()
    assert response.json()["service_date"] == expected_today


def test_service_summary_invalid_date_returns_422(seeded_gtfs_with_departures):
    response = client.get("/api/gtfs/agencies/CTA/routes/R1/service-summary?date=not-a-date")

    assert response.status_code == 422


@pytest.fixture
def seeded_gtfs_weekday_vs_weekend(tmp_path, monkeypatch):
    """Two separate service patterns: "WD" runs Mon-Fri only, "SAT" runs Saturdays only."""
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "weekday_weekend.db")
    database.init_db()
    gtfs_repository.insert_routes([("CTA", "R1", "1", "1", "Red Line", "1")])
    gtfs_repository.insert_calendar(
        [
            ("CTA", "WD", 1, 1, 1, 1, 1, 0, 0, "20200101", "20301231"),
            ("CTA", "SAT", 0, 0, 0, 0, 0, 1, 0, "20200101", "20301231"),
        ]
    )
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


def test_service_summary_tuesday_uses_only_weekday_service(seeded_gtfs_weekday_vs_weekend):
    # 2026-08-11 is a Tuesday.
    response = client.get("/api/gtfs/agencies/CTA/routes/R1/service-summary?date=2026-08-11")

    assert response.status_code == 200
    body = response.json()
    assert body["day_of_week"] == "Tuesday"
    assert body["active_service_ids"] == ["WD"]
    assert body["trip_count"] == 1
    assert body["first_departure_time"] == "08:00:00"


def test_service_summary_saturday_uses_only_weekend_service(seeded_gtfs_weekday_vs_weekend):
    # 2026-08-15 is a Saturday.
    response = client.get("/api/gtfs/agencies/CTA/routes/R1/service-summary?date=2026-08-15")

    assert response.status_code == 200
    body = response.json()
    assert body["day_of_week"] == "Saturday"
    assert body["active_service_ids"] == ["SAT"]
    assert body["trip_count"] == 1
    assert body["first_departure_time"] == "10:00:00"


def test_service_summary_calendar_dates_addition(seeded_gtfs_weekday_vs_weekend):
    # Add a one-off "SPECIAL" trip via calendar_dates for a Tuesday that
    # otherwise only has "WD" active.
    gtfs_repository.insert_trips([("CTA", "T3", "R1", "SPECIAL", "Downtown", "0")])
    gtfs_repository.insert_stop_times([("CTA", "T3", "S1", "12:00:00", "12:00:00", 1)])
    gtfs_repository.insert_calendar_dates([("CTA", "SPECIAL", "20260811", "1")])

    response = client.get("/api/gtfs/agencies/CTA/routes/R1/service-summary?date=2026-08-11")

    body = response.json()
    assert set(body["active_service_ids"]) == {"WD", "SPECIAL"}
    assert body["trip_count"] == 2  # the normal 08:00 "WD" trip plus the added 12:00 "SPECIAL" trip

    # The addition only applies to that exact date.
    other_day = client.get("/api/gtfs/agencies/CTA/routes/R1/service-summary?date=2026-08-12").json()
    assert "SPECIAL" not in other_day["active_service_ids"]


def test_service_summary_calendar_dates_removal(seeded_gtfs_weekday_vs_weekend):
    # Remove "WD" service on one specific Tuesday (e.g. a holiday closure).
    gtfs_repository.insert_calendar_dates([("CTA", "WD", "20260811", "2")])

    response = client.get("/api/gtfs/agencies/CTA/routes/R1/service-summary?date=2026-08-11")

    body = response.json()
    assert body["active_service_ids"] == []
    assert body["trip_count"] == 0
    assert body["first_departure_time"] is None
    assert body["average_headway_minutes"] is None

    # A different Tuesday without the exception still has "WD" active.
    other_day = client.get("/api/gtfs/agencies/CTA/routes/R1/service-summary?date=2026-08-18").json()
    assert other_day["active_service_ids"] == ["WD"]


def test_service_summary_no_active_service_returns_clean_empty_result(seeded_gtfs_weekday_vs_weekend):
    # A Wednesday: neither "WD"'s Tuesday-only stand-in nor "SAT" apply here
    # in this fixture's actual setup ("WD" *does* run weekdays, so pick a
    # date outside its calendar range instead to get zero active service).
    response = client.get("/api/gtfs/agencies/CTA/routes/R1/service-summary?date=2019-01-01")

    assert response.status_code == 200
    body = response.json()
    assert body["active_service_ids"] == []
    assert body["trip_count"] == 0
    assert body["first_departure_time"] is None
    assert body["last_departure_time"] is None
    assert body["average_headway_minutes"] is None
    assert body["peak_headway_minutes"] is None
    assert body["midday_headway_minutes"] is None
    assert body["evening_headway_minutes"] is None
    assert body["service_span_hours"] is None
    assert body["frequency_classification"] == "minimal"


def test_service_summary_multiple_inactive_services_do_not_affect_result(seeded_gtfs_weekday_vs_weekend):
    # Add a third, unrelated service pattern that never matches the
    # requested Tuesday and has no calendar_dates exception either.
    gtfs_repository.insert_calendar([("CTA", "SUN", 0, 0, 0, 0, 0, 0, 1, "20200101", "20301231")])
    gtfs_repository.insert_trips([("CTA", "T3", "R1", "SUN", "Downtown", "0")])
    gtfs_repository.insert_stop_times([("CTA", "T3", "S1", "11:00:00", "11:00:00", 1)])

    response = client.get("/api/gtfs/agencies/CTA/routes/R1/service-summary?date=2026-08-11")

    body = response.json()
    assert body["active_service_ids"] == ["WD"]
    assert body["trip_count"] == 1  # the inactive "SAT" and "SUN" trips are not counted
    assert body["first_departure_time"] == "08:00:00"


def test_service_summary_same_route_id_across_agencies_does_not_mix(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "agency_isolation.db")
    database.init_db()
    gtfs_repository.insert_routes(
        [
            ("CTA", "R1", "1", "1", "CTA Red Line", "1"),
            ("DART", "R1", "1", "1", "DART Red Line", "2"),
        ]
    )
    gtfs_repository.insert_calendar(
        [
            ("CTA", "WD", 1, 1, 1, 1, 1, 1, 1, "20200101", "20301231"),
            ("DART", "WD", 1, 1, 1, 1, 1, 1, 1, "20200101", "20301231"),
        ]
    )
    gtfs_repository.insert_trips(
        [
            ("CTA", "T1", "R1", "WD", "Downtown", "0"),
            ("DART", "T1", "R1", "WD", "Downtown", "0"),
        ]
    )
    gtfs_repository.insert_stop_times(
        [
            ("CTA", "T1", "S1", "08:00:00", "08:00:00", 1),
            ("DART", "T1", "S1", "09:30:00", "09:30:00", 1),
        ]
    )

    cta_response = client.get("/api/gtfs/agencies/CTA/routes/R1/service-summary?date=2026-08-11").json()
    dart_response = client.get("/api/gtfs/agencies/DART/routes/R1/service-summary?date=2026-08-11").json()

    assert cta_response["route_long_name"] == "CTA Red Line"
    assert cta_response["first_departure_time"] == "08:00:00"
    assert dart_response["route_long_name"] == "DART Red Line"
    assert dart_response["first_departure_time"] == "09:30:00"
