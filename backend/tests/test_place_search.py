"""Tests for app/services/place_search.py. Pure function, plain dict fixtures."""

from app.services.place_search import MAX_SUGGESTIONS, normalize_place_suggestions


def _prediction(place_id, main_text, secondary_text=None):
    structured = {"mainText": {"text": main_text}}
    if secondary_text:
        structured["secondaryText"] = {"text": secondary_text}
    return {"placePrediction": {"placeId": place_id, "structuredFormat": structured}}


def test_normalize_extracts_primary_and_secondary_text():
    raw = [_prediction("p1", "DFW International Airport", "Dallas, TX, USA")]

    result = normalize_place_suggestions(raw)

    assert len(result) == 1
    assert result[0].place_id == "p1"
    assert result[0].primary_text == "DFW International Airport"
    assert result[0].secondary_text == "Dallas, TX, USA"


def test_normalize_street_address_suggestion():
    # A partial street address query, e.g. "3532 La Playa" -- exercises the
    # same code path as any other prediction, since normalization doesn't
    # branch on place type.
    raw = [_prediction("addr-1", "3532 La Playa Dr", "Dallas, TX, USA")]

    result = normalize_place_suggestions(raw)

    assert result[0].label == "3532 La Playa Dr, Dallas, TX, USA"
    assert result[0].primary_text == "3532 La Playa Dr"
    assert result[0].secondary_text == "Dallas, TX, USA"


def test_normalize_airport_suggestion():
    raw = [_prediction("airport-1", "Dallas Fort Worth International Airport", "DFW Airport, TX, USA")]

    result = normalize_place_suggestions(raw)

    assert result[0].label == "Dallas Fort Worth International Airport, DFW Airport, TX, USA"
    assert result[0].place_id == "airport-1"


def test_normalize_label_combines_primary_and_secondary():
    raw = [_prediction("p1", "Union Station", "Dallas, TX, USA")]

    result = normalize_place_suggestions(raw)

    assert result[0].label == "Union Station, Dallas, TX, USA"


def test_normalize_label_falls_back_to_primary_text_only():
    raw = [_prediction("p1", "Just a name")]

    result = normalize_place_suggestions(raw)

    assert result[0].label == "Just a name"


def test_normalize_dedupes_by_place_id_keeping_first_occurrence():
    raw = [_prediction("p1", "First Text"), _prediction("p1", "Duplicate, Should Be Dropped")]

    result = normalize_place_suggestions(raw)

    assert len(result) == 1
    assert result[0].primary_text == "First Text"


def test_normalize_skips_missing_place_id():
    raw = [{"placePrediction": {"structuredFormat": {"mainText": {"text": "No id"}}}}]

    assert normalize_place_suggestions(raw) == []


def test_normalize_skips_missing_main_text():
    raw = [{"placePrediction": {"placeId": "p1"}}]

    assert normalize_place_suggestions(raw) == []


def test_normalize_secondary_text_defaults_to_none():
    raw = [_prediction("p1", "Just a name")]

    result = normalize_place_suggestions(raw)

    assert result[0].secondary_text is None


def test_normalize_caps_at_max_suggestions():
    raw = [_prediction(f"p{i}", f"Place {i}") for i in range(MAX_SUGGESTIONS + 5)]

    result = normalize_place_suggestions(raw)

    assert len(result) == MAX_SUGGESTIONS
    assert result[0].place_id == "p0"


def test_normalize_empty_input_returns_empty_list():
    assert normalize_place_suggestions([]) == []
