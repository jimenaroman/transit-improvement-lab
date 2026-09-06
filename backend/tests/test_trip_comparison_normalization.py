"""
Tests for app/services/trip_comparison.py. Pure functions, plain dict
fixtures shaped like real Google Routes API responses -- no network, no DB.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from app.services.trip_comparison import (
    REPRESENTATIVE_HOUR,
    TripComparisonError,
    build_trip_verdict,
    calculate_trip_transit_penalty,
    extract_transit_lines,
    normalize_drive_route,
    normalize_transit_route,
    resolve_representative_departure_time,
)

CENTRAL = ZoneInfo("America/Chicago")

DRIVE_RESPONSE = {
    "routes": [
        {
            "duration": "840s",
            "distanceMeters": 7724,
            "polyline": {"encodedPolyline": "abc123"},
        }
    ]
}

TRANSIT_RESPONSE = {
    "routes": [
        {
            "duration": "1860s",
            "distanceMeters": 8368,
            "polyline": {"encodedPolyline": "xyz789"},
            "legs": [
                {
                    "steps": [
                        {"travelMode": "WALK", "staticDuration": "360s"},
                        {
                            "travelMode": "TRANSIT",
                            "transitDetails": {
                                "headsign": "Downtown",
                                "transitLine": {
                                    "name": "DALLAS STREETCAR",
                                    "nameShort": "620",
                                    "agencies": [{"name": "DALLAS AREA RAPID TRANSIT"}],
                                },
                            },
                        },
                        {"travelMode": "WALK", "staticDuration": "300s"},
                    ]
                }
            ],
        }
    ]
}


def test_normalize_drive_route_parses_duration_distance_polyline():
    driving = normalize_drive_route(DRIVE_RESPONSE)

    assert driving.duration_minutes == 14
    assert driving.distance_miles == 4.8
    assert driving.polyline == "abc123"


def test_normalize_drive_route_missing_routes_raises():
    with pytest.raises(TripComparisonError):
        normalize_drive_route({"routes": []})


def test_normalize_drive_route_no_routes_key_raises():
    with pytest.raises(TripComparisonError):
        normalize_drive_route({})


def test_normalize_transit_route_sums_walking_and_counts_transfers():
    transit = normalize_transit_route(TRANSIT_RESPONSE)

    assert transit.duration_minutes == 31
    assert transit.walking_minutes == 11  # 360s + 300s = 660s = 11 min
    assert transit.transfers == 0  # one transit step -> no transfer
    assert transit.route_names == ["620"]
    assert transit.polyline == "xyz789"


def test_normalize_transit_route_two_transit_steps_is_one_transfer():
    two_leg_response = {
        "routes": [
            {
                "duration": "2000s",
                "legs": [
                    {
                        "steps": [
                            {
                                "travelMode": "TRANSIT",
                                "transitDetails": {
                                    "transitLine": {"nameShort": "6", "agencies": [{"name": "Chicago Transit Authority"}]}
                                },
                            },
                            {
                                "travelMode": "TRANSIT",
                                "transitDetails": {
                                    "transitLine": {"nameShort": "8", "agencies": [{"name": "Chicago Transit Authority"}]}
                                },
                            },
                        ]
                    }
                ],
            }
        ]
    }

    transit = normalize_transit_route(two_leg_response)

    assert transit.transfers == 1
    assert transit.route_names == ["6", "8"]


def test_normalize_transit_route_prefers_short_name_and_dedupes():
    response = {
        "routes": [
            {
                "duration": "100s",
                "legs": [
                    {
                        "steps": [
                            {
                                "travelMode": "TRANSIT",
                                "transitDetails": {"transitLine": {"name": "Long Name Only"}},
                            },
                            {
                                "travelMode": "TRANSIT",
                                "transitDetails": {
                                    "transitLine": {"name": "Should be ignored", "nameShort": "Long Name Only"}
                                },
                            },
                        ]
                    }
                ],
            }
        ]
    }

    transit = normalize_transit_route(response)

    # Falls back to full name when nameShort is absent, then dedupes
    # against the second step's nameShort that happens to match it.
    assert transit.route_names == ["Long Name Only"]


def test_normalize_transit_route_no_transit_steps_is_pure_walk():
    walk_only = {"routes": [{"duration": "600s", "legs": [{"steps": [{"travelMode": "WALK", "staticDuration": "600s"}]}]}]}

    transit = normalize_transit_route(walk_only)

    assert transit.transfers == 0
    assert transit.route_names == []


def test_normalize_transit_route_malformed_missing_legs_does_not_crash():
    transit = normalize_transit_route({"routes": [{"duration": "500s"}]})

    assert transit.duration_minutes == 8
    assert transit.walking_minutes == 0
    assert transit.transfers == 0
    assert transit.route_names == []


def test_extract_transit_lines_missing_agency_is_none():
    response = {
        "routes": [
            {
                "legs": [
                    {
                        "steps": [
                            {
                                "travelMode": "TRANSIT",
                                "transitDetails": {"transitLine": {"nameShort": "42"}},
                            }
                        ]
                    }
                ]
            }
        ]
    }

    lines = extract_transit_lines(response)

    assert lines == [{"agency_name": None, "route_short_name": "42", "route_long_name": None, "headsign": None}]


def test_calculate_trip_transit_penalty():
    assert calculate_trip_transit_penalty(31, 14) == 2.21


def test_calculate_trip_transit_penalty_zero_driving_minutes_raises():
    with pytest.raises(TripComparisonError):
        calculate_trip_transit_penalty(30, 0)


def test_build_trip_verdict_faster_than_driving():
    assert "as fast as or faster" in build_trip_verdict(0)
    assert "as fast as or faster" in build_trip_verdict(-5)


def test_build_trip_verdict_competitive():
    assert "roughly competitive" in build_trip_verdict(10)


def test_build_trip_verdict_meaningfully_longer():
    assert "meaningfully longer" in build_trip_verdict(11)


def test_resolve_representative_departure_time_is_a_weekday():
    # 2026-09-08 is a Tuesday; well after 9am, so it should roll to Wednesday.
    now = datetime(2026, 9, 8, 14, 30, tzinfo=CENTRAL)

    departure = resolve_representative_departure_time(now)

    assert departure.weekday() < 5
    assert departure.hour == REPRESENTATIVE_HOUR
    assert departure > now


def test_resolve_representative_departure_time_skips_weekend():
    # 2026-09-12 is a Saturday -> should roll forward to Monday 2026-09-14.
    now = datetime(2026, 9, 12, 10, 0, tzinfo=CENTRAL)

    departure = resolve_representative_departure_time(now)

    assert departure.date().isoformat() == "2026-09-14"
    assert departure.weekday() == 0  # Monday


def test_resolve_representative_departure_time_same_day_if_still_ahead():
    # 2026-09-08 is a Tuesday, 6am -- 9am the same day is still ahead of now.
    now = datetime(2026, 9, 8, 6, 0, tzinfo=CENTRAL)

    departure = resolve_representative_departure_time(now)

    assert departure.date().isoformat() == "2026-09-08"
    assert departure.hour == REPRESENTATIVE_HOUR


def test_resolve_representative_departure_time_is_always_in_the_future():
    # Exactly at the representative hour -- must roll forward, not return "now".
    now = datetime(2026, 9, 8, REPRESENTATIVE_HOUR, 0, tzinfo=CENTRAL)

    departure = resolve_representative_departure_time(now)

    assert departure > now
