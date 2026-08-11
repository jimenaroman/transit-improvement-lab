"""
Tests for services/gtfs_metrics.py.

No database here on purpose — this module takes plain values (departure
time strings, calendar rows, a timezone name) and returns plain values, so
these tests call it directly.
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.services.gtfs_metrics import (
    calculate_service_summary,
    compute_active_service_ids,
    parse_gtfs_time_to_minutes,
    resolve_service_date,
)


def test_parse_gtfs_time_handles_normal_and_after_midnight_times():
    assert parse_gtfs_time_to_minutes("08:00:00") == 480
    assert parse_gtfs_time_to_minutes("25:30:00") == 1530  # after-midnight, not wrapped to 01:30


def test_normal_headway_calculation():
    # Four evenly spaced midday departures, 15 minutes apart.
    departures = ["09:00:00", "09:15:00", "09:30:00", "09:45:00"]

    summary = calculate_service_summary(departures)

    assert summary["trip_count"] == 4
    assert summary["first_departure_time"] == "09:00:00"
    assert summary["last_departure_time"] == "09:45:00"
    assert summary["average_headway_minutes"] == 15.0
    assert summary["midday_headway_minutes"] == 15.0
    assert summary["peak_headway_minutes"] is None
    assert summary["evening_headway_minutes"] is None


def test_after_midnight_departure_is_last_and_unwrapped():
    departures = ["09:00:00", "09:15:00", "25:30:00"]

    summary = calculate_service_summary(departures)

    assert summary["trip_count"] == 3
    assert summary["last_departure_time"] == "25:30:00"


def test_fewer_than_two_departures_returns_null_overall_headway():
    summary = calculate_service_summary(["09:00:00"])

    assert summary["trip_count"] == 1
    assert summary["first_departure_time"] == "09:00:00"
    assert summary["last_departure_time"] == "09:00:00"
    assert summary["average_headway_minutes"] is None


def test_zero_departures_returns_all_nulls():
    summary = calculate_service_summary([])

    assert summary["trip_count"] == 0
    assert summary["first_departure_time"] is None
    assert summary["last_departure_time"] is None
    assert summary["average_headway_minutes"] is None
    assert summary["peak_headway_minutes"] is None
    assert summary["midday_headway_minutes"] is None
    assert summary["evening_headway_minutes"] is None


def test_windows_calculate_independently():
    departures = [
        "08:00:00", "08:20:00",  # peak (morning): gap 20
        "10:00:00", "10:30:00",  # midday: gap 30
        "19:00:00", "19:10:00",  # evening: gap 10
    ]

    summary = calculate_service_summary(departures)

    assert summary["peak_headway_minutes"] == 20.0
    assert summary["midday_headway_minutes"] == 30.0
    assert summary["evening_headway_minutes"] == 10.0


def test_peak_window_pools_morning_and_evening_rush_gaps():
    # Morning peak: 08:00, 08:10 -> gap 10. Evening peak: 17:00, 17:20 -> gap 20.
    # Pooled average across both sub-windows: (10 + 20) / 2 = 15.
    departures = ["08:00:00", "08:10:00", "17:00:00", "17:20:00"]

    summary = calculate_service_summary(departures)

    assert summary["peak_headway_minutes"] == 15.0


def test_peak_window_does_not_bridge_gap_between_morning_and_evening():
    # One departure in morning peak, one in evening peak, nothing else.
    # There's no meaningful "headway" between them -- that's the midday
    # gap in service, not peak frequency -- so this must be null, not a
    # huge multi-hour average.
    departures = ["08:00:00", "17:00:00"]

    summary = calculate_service_summary(departures)

    assert summary["peak_headway_minutes"] is None


def test_departures_outside_all_named_windows_still_count_toward_trip_count():
    # 05:00 and 23:00 are outside peak/midday/evening entirely.
    departures = ["05:00:00", "23:00:00"]

    summary = calculate_service_summary(departures)

    assert summary["trip_count"] == 2
    assert summary["average_headway_minutes"] == 18 * 60  # gap between 05:00 and 23:00
    assert summary["peak_headway_minutes"] is None
    assert summary["midday_headway_minutes"] is None
    assert summary["evening_headway_minutes"] is None


def test_resolve_service_date_uses_explicit_date_when_given():
    explicit = date(2026, 8, 11)

    resolved = resolve_service_date(explicit, agency_timezone="America/Chicago")

    assert resolved == explicit


def test_resolve_service_date_falls_back_to_default_timezone_when_missing():
    resolved_with_none = resolve_service_date(None, agency_timezone=None)
    expected = resolve_service_date(None, agency_timezone="America/Chicago")

    assert resolved_with_none == expected


def test_resolve_service_date_falls_back_on_unknown_timezone_name():
    resolved = resolve_service_date(None, agency_timezone="Not/A_Real_Zone")
    expected = resolve_service_date(None, agency_timezone="America/Chicago")

    assert resolved == expected


def test_resolve_service_date_matches_wall_clock_in_that_timezone():
    resolved = resolve_service_date(None, agency_timezone="America/Chicago")

    assert resolved == datetime.now(ZoneInfo("America/Chicago")).date()


def test_compute_active_service_ids_with_no_exceptions():
    active = compute_active_service_ids(["WD"], [])

    assert active == ["WD"]


def test_compute_active_service_ids_addition():
    active = compute_active_service_ids(["WD"], [("HOLIDAY", "1")])

    assert active == ["HOLIDAY", "WD"]


def test_compute_active_service_ids_removal():
    active = compute_active_service_ids(["WD"], [("WD", "2")])

    assert active == []


def test_compute_active_service_ids_addition_and_removal_together():
    active = compute_active_service_ids(["WD", "SAT"], [("WD", "2"), ("HOLIDAY", "1")])

    assert active == ["HOLIDAY", "SAT"]
