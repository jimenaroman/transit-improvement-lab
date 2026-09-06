"""
Normalizes raw Google Places Autocomplete JSON (from
app/clients/google_places_client.py) into PlaceSuggestion models.

Pure functions only -- no HTTP, no SQL. See docs/architecture.md.
"""

from app.trip_compare_schemas import PlaceSuggestion

MAX_SUGGESTIONS = 8


def normalize_place_suggestions(raw_suggestions: list[dict]) -> list[PlaceSuggestion]:
    """
    Deduplicates by place_id (the Dallas-biased and Chicago-biased calls
    can return the same place) and keeps the first occurrence's order,
    capped at MAX_SUGGESTIONS. Skips any suggestion missing a placeId or
    main text -- malformed rather than guessed.
    """
    suggestions: list[PlaceSuggestion] = []
    seen_place_ids: set[str] = set()

    for raw in raw_suggestions:
        prediction = raw.get("placePrediction", {})
        place_id = prediction.get("placeId")
        main_text = prediction.get("structuredFormat", {}).get("mainText", {}).get("text")

        if not place_id or not main_text or place_id in seen_place_ids:
            continue

        secondary_text = prediction.get("structuredFormat", {}).get("secondaryText", {}).get("text")
        label = f"{main_text}, {secondary_text}" if secondary_text else main_text

        seen_place_ids.add(place_id)
        suggestions.append(
            PlaceSuggestion(
                label=label,
                place_id=place_id,
                primary_text=main_text,
                secondary_text=secondary_text,
            )
        )

        if len(suggestions) >= MAX_SUGGESTIONS:
            break

    return suggestions
