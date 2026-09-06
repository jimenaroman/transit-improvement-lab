"""
Normalizes raw Google Routes API JSON (from app/clients/google_routes_client.py)
into this app's own DrivingSummary/TransitSummary models, plus the small
transit-penalty/verdict math for the arbitrary-trip comparison.

Pure functions only -- no HTTP, no SQL. See docs/architecture.md.
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.trip_compare_schemas import DrivingSummary, TransitSummary

METERS_PER_MILE = 1609.344

# extra_minutes at or below this is "roughly competitive" -- same threshold
# concept as simulator.py's COMPETITIVE_GAP_MINUTES, kept separate since
# this module doesn't operate on a RouteScenario.
COMPETITIVE_GAP_MINUTES = 10

# Both agencies this app imports (CTA, DART) operate in Central time, so one
# timezone is enough for a representative-time heuristic -- not a general
# multi-timezone assumption.
REPRESENTATIVE_TIMEZONE = "America/Chicago"
REPRESENTATIVE_HOUR = 9  # a typical weekday daytime hour, not pre-dawn or late-night service


def resolve_representative_departure_time(now: datetime | None = None) -> datetime:
    """
    Returns the next weekday at REPRESENTATIVE_HOUR:00 in REPRESENTATIVE_TIMEZONE,
    strictly after `now` -- never "now" itself. Deliberately not a fixed
    calendar date: Google's TRANSIT mode rejects a departureTime in the
    past, and a fixed date would eventually become one.

    `now` is only for tests; production callers always use the default.
    """
    current = now or datetime.now(ZoneInfo(REPRESENTATIVE_TIMEZONE))
    candidate = current.replace(hour=REPRESENTATIVE_HOUR, minute=0, second=0, microsecond=0)

    if candidate <= current:
        candidate += timedelta(days=1)
    while candidate.weekday() >= 5:  # Saturday=5, Sunday=6
        candidate += timedelta(days=1)

    return candidate


class TripComparisonError(Exception):
    """Raised when a Google Routes response has no usable route to normalize."""


def _parse_duration_minutes(duration: str | None) -> int:
    """Google's "duration" is a Duration-protobuf string like "930s". Missing/unparseable -> 0."""
    if not duration or not duration.endswith("s"):
        return 0
    try:
        return round(float(duration[:-1]) / 60)
    except ValueError:
        return 0


def _meters_to_miles(distance_meters: int | float | None) -> float | None:
    return round(distance_meters / METERS_PER_MILE, 1) if distance_meters is not None else None


def _first_route(raw_response: dict) -> dict:
    routes = raw_response.get("routes")
    if not routes:
        raise TripComparisonError("Google Routes API returned no routes for this origin/destination.")
    return routes[0]


def normalize_drive_route(raw_response: dict) -> DrivingSummary:
    route = _first_route(raw_response)

    return DrivingSummary(
        duration_minutes=_parse_duration_minutes(route.get("duration")),
        distance_miles=_meters_to_miles(route.get("distanceMeters")),
        polyline=route.get("polyline", {}).get("encodedPolyline"),
    )


def extract_transit_lines(raw_response: dict) -> list[dict]:
    """
    Returns one dict per TRANSIT-mode step across every leg, in itinerary
    order: {agency_name, route_short_name, route_long_name, headsign}.
    Used both for TransitSummary.route_names and for GTFS matching.
    """
    route = _first_route(raw_response)
    lines = []

    for leg in route.get("legs", []):
        for step in leg.get("steps", []):
            if step.get("travelMode") != "TRANSIT":
                continue

            transit_details = step.get("transitDetails", {})
            transit_line = transit_details.get("transitLine", {})
            agencies = transit_line.get("agencies", [])

            lines.append(
                {
                    "agency_name": agencies[0]["name"] if agencies else None,
                    "route_short_name": transit_line.get("nameShort"),
                    "route_long_name": transit_line.get("name"),
                    "headsign": transit_details.get("headsign"),
                }
            )

    return lines


def normalize_transit_route(raw_response: dict) -> TransitSummary:
    route = _first_route(raw_response)
    steps = [step for leg in route.get("legs", []) for step in leg.get("steps", [])]

    walking_minutes = sum(
        _parse_duration_minutes(step.get("staticDuration")) for step in steps if step.get("travelMode") == "WALK"
    )
    transit_step_count = sum(1 for step in steps if step.get("travelMode") == "TRANSIT")

    route_names = []
    for line in extract_transit_lines(raw_response):
        name = line["route_short_name"] or line["route_long_name"]
        if name and name not in route_names:
            route_names.append(name)

    return TransitSummary(
        duration_minutes=_parse_duration_minutes(route.get("duration")),
        distance_miles=_meters_to_miles(route.get("distanceMeters")),
        walking_minutes=walking_minutes,
        transfers=max(transit_step_count - 1, 0),
        route_names=route_names,
        polyline=route.get("polyline", {}).get("encodedPolyline"),
    )


def calculate_trip_transit_penalty(transit_minutes: int, driving_minutes: int) -> float:
    if driving_minutes <= 0:
        raise TripComparisonError("Driving minutes must be greater than zero.")

    return round(transit_minutes / driving_minutes, 2)


def build_trip_verdict(extra_minutes: int) -> str:
    if extra_minutes <= 0:
        return "Transit is as fast as or faster than driving for this trip."
    if extra_minutes <= COMPETITIVE_GAP_MINUTES:
        return "Transit is roughly competitive with driving for this trip."
    return "Transit takes meaningfully longer than driving for this trip."
