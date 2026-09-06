"""
GET /api/places/autocomplete -- proxies Google Places Autocomplete so the
API key never reaches the frontend. See docs/google-routes-integration.md.
"""

from fastapi import APIRouter, HTTPException, Query

from app.clients.google_places_client import GooglePlacesApiError, fetch_autocomplete_suggestions
from app.services.place_search import normalize_place_suggestions
from app.trip_compare_schemas import PlaceSuggestion

router = APIRouter(prefix="/api/places", tags=["places"])


@router.get("/autocomplete", response_model=list[PlaceSuggestion])
def autocomplete(
    input: str = Query(..., min_length=1, description="Partial address/place text the user has typed."),
) -> list[PlaceSuggestion]:
    try:
        raw_suggestions = fetch_autocomplete_suggestions(input)
    except GooglePlacesApiError as error:
        raise HTTPException(status_code=502, detail="Could not reach the places service.") from error

    return normalize_place_suggestions(raw_suggestions)
