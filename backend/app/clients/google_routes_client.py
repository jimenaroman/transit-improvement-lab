"""
Thin client for Google's Routes API (POST .../directions/v2:computeRoutes).

Returns parsed JSON only -- no normalization into app models, that's
services/trip_comparison.py's job. See docs/architecture.md for the
clients/ vs. services/ split, and docs/google-routes-integration.md for
the request/response contract this app actually uses.
"""

from datetime import datetime

import httpx

from app.config import get_google_maps_api_key
from app.trip_compare_schemas import LocationInput

COMPUTE_ROUTES_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"
REQUEST_TIMEOUT_SECONDS = 10.0

# Field masks are scoped to only what this app reads -- Google bills by
# which fields are requested, so asking for more than we use costs more.
DRIVE_FIELD_MASK = "routes.duration,routes.distanceMeters,routes.polyline.encodedPolyline"
TRANSIT_FIELD_MASK = (
    "routes.duration,routes.distanceMeters,routes.polyline.encodedPolyline,"
    "routes.legs.steps.travelMode,routes.legs.steps.distanceMeters,"
    "routes.legs.steps.staticDuration,routes.legs.steps.transitDetails"
)


class GoogleRoutesApiError(Exception):
    """Raised for a missing key, a failed HTTP call, a timeout, or an unparseable response.

    Never construct this with the raw API key in the message.
    """


def _to_waypoint(location: LocationInput) -> dict:
    """place_id (a stable, unambiguous autocomplete selection) wins over the raw label."""
    return {"placeId": location.place_id} if location.place_id else {"address": location.label}


def _compute_routes(
    origin: LocationInput,
    destination: LocationInput,
    travel_mode: str,
    field_mask: str,
    departure_time: datetime | None = None,
) -> dict:
    api_key = get_google_maps_api_key()
    if not api_key:
        raise GoogleRoutesApiError("GOOGLE_MAPS_API_KEY is not configured.")

    request_body: dict = {
        "origin": _to_waypoint(origin),
        "destination": _to_waypoint(destination),
        "travelMode": travel_mode,
        "computeAlternativeRoutes": False,
    }
    if travel_mode == "DRIVE":
        request_body["routingPreference"] = "TRAFFIC_UNAWARE"
    if departure_time is not None:
        request_body["departureTime"] = departure_time.isoformat()

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": field_mask,
    }

    try:
        response = httpx.post(
            COMPUTE_ROUTES_URL, json=request_body, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as error:
        raise GoogleRoutesApiError(f"Google Routes API returned {error.response.status_code}.") from error
    except httpx.HTTPError as error:
        raise GoogleRoutesApiError(f"Google Routes API request failed: {type(error).__name__}.") from error

    try:
        return response.json()
    except ValueError as error:
        raise GoogleRoutesApiError("Google Routes API returned a non-JSON response.") from error


def fetch_drive_route(origin: LocationInput, destination: LocationInput) -> dict:
    # No departureTime: TRAFFIC_UNAWARE gives a typical/average time regardless of when asked.
    return _compute_routes(origin, destination, "DRIVE", DRIVE_FIELD_MASK)


def fetch_transit_route(origin: LocationInput, destination: LocationInput, departure_time: datetime) -> dict:
    return _compute_routes(origin, destination, "TRANSIT", TRANSIT_FIELD_MASK, departure_time=departure_time)
