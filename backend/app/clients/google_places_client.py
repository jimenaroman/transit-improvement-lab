"""
Thin client for Google's Places API (New) Autocomplete
(POST .../v1/places:autocomplete). Returns parsed JSON only -- no
normalization, that's services/place_search.py's job. See
docs/architecture.md and docs/google-routes-integration.md.
"""

import httpx

from app.config import get_google_maps_api_key

AUTOCOMPLETE_URL = "https://places.googleapis.com/v1/places:autocomplete"
REQUEST_TIMEOUT_SECONDS = 8.0
FIELD_MASK = "suggestions.placePrediction.placeId,suggestions.placePrediction.structuredFormat"

# locationBias supports only one region per call, and Dallas/Chicago are
# ~800 miles apart -- one shared bounding shape would barely bias anything.
# Two calls, one per metro, merged by the service layer, actually prefers
# both instead of diluting toward neither.
DALLAS_BIAS = {"latitude": 32.7767, "longitude": -96.7970}
CHICAGO_BIAS = {"latitude": 41.8781, "longitude": -87.6298}
BIAS_RADIUS_METERS = 50000.0  # Places API's documented max circle radius


class GooglePlacesApiError(Exception):
    """Raised for a missing key, a failed HTTP call, a timeout, or an unparseable response.

    Never construct this with the raw API key in the message.
    """


def _autocomplete_biased(input_text: str, center: dict) -> list[dict]:
    api_key = get_google_maps_api_key()
    if not api_key:
        raise GooglePlacesApiError("GOOGLE_MAPS_API_KEY is not configured.")

    request_body = {
        "input": input_text,
        "includedRegionCodes": ["us"],
        "locationBias": {"circle": {"center": center, "radius": BIAS_RADIUS_METERS}},
    }
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": FIELD_MASK,
    }

    try:
        response = httpx.post(
            AUTOCOMPLETE_URL, json=request_body, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as error:
        raise GooglePlacesApiError(f"Google Places API returned {error.response.status_code}.") from error
    except httpx.HTTPError as error:
        raise GooglePlacesApiError(f"Google Places API request failed: {type(error).__name__}.") from error

    try:
        return response.json().get("suggestions", [])
    except ValueError as error:
        raise GooglePlacesApiError("Google Places API returned a non-JSON response.") from error


def fetch_autocomplete_suggestions(input_text: str) -> list[dict]:
    """Raw suggestions biased toward Dallas, then Chicago -- concatenated, not deduped yet."""
    return _autocomplete_biased(input_text, DALLAS_BIAS) + _autocomplete_biased(input_text, CHICAGO_BIAS)
