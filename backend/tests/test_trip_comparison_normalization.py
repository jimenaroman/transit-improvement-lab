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
    build_transit_itinerary,
    build_trip_verdict,
    calculate_trip_transit_penalty,
    extract_route_segments,
    extract_transit_lines,
    normalize_drive_route,
    normalize_transit_route,
    resolve_representative_departure_time,
    total_riding_minutes,
    total_wait_minutes,
)
from app.trip_compare_schemas import TripItineraryLeg

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
                        {
                            "travelMode": "WALK",
                            "staticDuration": "360s",
                            "polyline": {"encodedPolyline": "walk1"},
                        },
                        {
                            "travelMode": "TRANSIT",
                            "polyline": {"encodedPolyline": "transit1"},
                            "transitDetails": {
                                "headsign": "Downtown",
                                "transitLine": {
                                    "name": "DALLAS STREETCAR",
                                    "nameShort": "620",
                                    "agencies": [{"name": "DALLAS AREA RAPID TRANSIT"}],
                                },
                            },
                        },
                        {
                            "travelMode": "WALK",
                            "staticDuration": "300s",
                            "polyline": {"encodedPolyline": "walk2"},
                        },
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
    assert transit.riding_minutes == 0  # this fixture's TRANSIT step has no staticDuration
    assert transit.wait_minutes == 0  # single ride -> no transfers -> known zero, not missing
    assert transit.transfers == 0  # one transit step -> no transfer
    assert transit.route_names == ["620"]
    assert transit.polyline == "xyz789"
    assert [(s.travel_mode, s.polyline) for s in transit.segments] == [
        ("WALK", "walk1"),
        ("TRANSIT", "transit1"),
        ("WALK", "walk2"),
    ]


def test_extract_route_segments_missing_polyline_is_none():
    response = {"routes": [{"legs": [{"steps": [{"travelMode": "WALK"}]}]}]}

    segments = extract_route_segments(response)

    assert len(segments) == 1
    assert segments[0].travel_mode == "WALK"
    assert segments[0].polyline is None


def test_extract_route_segments_skips_step_with_no_travel_mode():
    response = {"routes": [{"legs": [{"steps": [{"polyline": {"encodedPolyline": "x"}}]}]}]}

    assert extract_route_segments(response) == []


def test_extract_route_segments_empty_when_no_legs():
    assert extract_route_segments({"routes": [{}]}) == []


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


def _transit_step(name_short, static_duration, arrival_time=None, departure_time=None):
    stop_details = {}
    if arrival_time:
        stop_details["arrivalTime"] = arrival_time
    if departure_time:
        stop_details["departureTime"] = departure_time
    return {
        "travelMode": "TRANSIT",
        "staticDuration": static_duration,
        "transitDetails": {"transitLine": {"nameShort": name_short}, "stopDetails": stop_details},
    }


def _walk_step(static_duration):
    return {"travelMode": "WALK", "staticDuration": static_duration}


def test_build_transit_itinerary_multi_transfer_uses_real_timestamp_gaps():
    # Mirrors a real La Playa Dr -> DFW Airport response: lead walk, bus,
    # transfer walk (folded into the wait), rail, rail, no trailing walk.
    response = {
        "routes": [
            {
                "legs": [
                    {
                        "steps": [
                            _walk_step("59s"),
                            _walk_step("467s"),
                            _transit_step(
                                "057", "318s", arrival_time="2026-09-07T14:23:00Z"
                            ),
                            _walk_step("41s"),
                            _transit_step(
                                "RED",
                                "1350s",
                                departure_time="2026-09-07T14:31:30Z",
                                arrival_time="2026-09-07T14:54:00Z",
                            ),
                            _transit_step("ORANGE", "3180s", departure_time="2026-09-07T15:01:00Z"),
                        ]
                    }
                ]
            }
        ]
    }

    legs = build_transit_itinerary(response)

    assert [(leg.kind, leg.label, leg.duration_minutes) for leg in legs] == [
        ("walk", "Walk", 9),  # 59+467=526s -> 8.77 -> rounds to 9
        ("ride", "057", 5),  # 318s -> 5.3 -> rounds to 5
        ("wait", "Transfer", 8),  # 14:23:00 -> 14:31:30 = 8.5min, walk step's 41s is absorbed into this
        ("ride", "RED", 22),  # 1350s -> 22.5 -> Python's round() rounds .5 to even -> 22
        ("wait", "Transfer", 7),  # 14:54:00 -> 15:01:00 = 7min exactly
        ("ride", "ORANGE", 53),  # 3180s -> 53.0
    ]


def test_build_transit_itinerary_missing_timestamp_gives_none_not_a_guess():
    response = {
        "routes": [
            {
                "legs": [
                    {
                        "steps": [
                            _transit_step("A", "300s", arrival_time="2026-09-07T14:00:00Z"),
                            _transit_step("B", "300s"),  # no departureTime at all
                        ]
                    }
                ]
            }
        ]
    }

    legs = build_transit_itinerary(response)
    wait_leg = next(leg for leg in legs if leg.kind == "wait")

    assert wait_leg.duration_minutes is None


def test_build_transit_itinerary_no_transit_steps_is_one_walk_leg():
    response = {"routes": [{"legs": [{"steps": [_walk_step("600s")]}]}]}

    legs = build_transit_itinerary(response)

    assert len(legs) == 1
    assert legs[0].kind == "walk"
    assert legs[0].duration_minutes == 10


def test_build_transit_itinerary_no_steps_at_all_is_empty():
    assert build_transit_itinerary({"routes": [{}]}) == []


def test_build_transit_itinerary_single_ride_no_walk_no_wait():
    response = {"routes": [{"legs": [{"steps": [_transit_step("RED", "600s")]}]}]}

    legs = build_transit_itinerary(response)

    assert [(leg.kind, leg.label, leg.duration_minutes) for leg in legs] == [("ride", "RED", 10)]


def test_build_transit_itinerary_falls_back_to_long_name():
    step = _transit_step(None, "600s")
    step["transitDetails"]["transitLine"]["name"] = "DART LIGHT RAIL - RED LINE"
    response = {"routes": [{"legs": [{"steps": [step]}]}]}

    legs = build_transit_itinerary(response)

    assert legs[0].label == "DART LIGHT RAIL - RED LINE"


def test_total_riding_minutes_sums_only_ride_legs():
    itinerary = [
        TripItineraryLeg(kind="walk", label="Walk", duration_minutes=5),
        TripItineraryLeg(kind="ride", label="057", duration_minutes=10),
        TripItineraryLeg(kind="wait", label="Transfer", duration_minutes=8),
        TripItineraryLeg(kind="ride", label="RED", duration_minutes=22),
    ]

    assert total_riding_minutes(itinerary) == 32


def test_total_riding_minutes_empty_itinerary_is_zero():
    assert total_riding_minutes([]) == 0


def test_total_wait_minutes_sums_wait_legs():
    itinerary = [
        TripItineraryLeg(kind="ride", label="057", duration_minutes=10),
        TripItineraryLeg(kind="wait", label="Transfer", duration_minutes=8),
        TripItineraryLeg(kind="ride", label="RED", duration_minutes=22),
        TripItineraryLeg(kind="wait", label="Transfer", duration_minutes=7),
        TripItineraryLeg(kind="ride", label="ORANGE", duration_minutes=53),
    ]

    assert total_wait_minutes(itinerary) == 15


def test_total_wait_minutes_zero_transfers_is_zero_not_none():
    itinerary = [TripItineraryLeg(kind="ride", label="RED", duration_minutes=10)]

    assert total_wait_minutes(itinerary) == 0


def test_total_wait_minutes_none_if_any_wait_leg_unknown():
    itinerary = [
        TripItineraryLeg(kind="ride", label="A", duration_minutes=10),
        TripItineraryLeg(kind="wait", label="Transfer", duration_minutes=None),
        TripItineraryLeg(kind="ride", label="B", duration_minutes=10),
    ]

    assert total_wait_minutes(itinerary) is None
