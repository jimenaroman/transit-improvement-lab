"""
Tests for GET /api/places/autocomplete. Google Places calls are
monkeypatched at the app.routes.places import site -- no real network calls.
"""

from fastapi.testclient import TestClient

from app.clients.google_places_client import GooglePlacesApiError
from app.main import app

client = TestClient(app)


def _prediction(place_id, main_text, secondary_text=None):
    structured = {"mainText": {"text": main_text}}
    if secondary_text:
        structured["secondaryText"] = {"text": secondary_text}
    return {"placePrediction": {"placeId": place_id, "structuredFormat": structured}}


def _patch_places(monkeypatch, suggestions=None, error=None):
    import app.routes.places as places_module

    def fake_fetch(input_text):
        if error:
            raise error
        return suggestions

    monkeypatch.setattr(places_module, "fetch_autocomplete_suggestions", fake_fetch)


def test_autocomplete_returns_normalized_suggestions(monkeypatch):
    _patch_places(monkeypatch, suggestions=[_prediction("p1", "DFW International Airport", "Dallas, TX, USA")])

    response = client.get("/api/places/autocomplete", params={"input": "dfw"})

    assert response.status_code == 200
    body = response.json()
    assert body == [
        {
            "label": "DFW International Airport, Dallas, TX, USA",
            "place_id": "p1",
            "primary_text": "DFW International Airport",
            "secondary_text": "Dallas, TX, USA",
        }
    ]


def test_autocomplete_requires_input_param():
    response = client.get("/api/places/autocomplete")

    assert response.status_code == 422


def test_autocomplete_rejects_empty_input():
    response = client.get("/api/places/autocomplete", params={"input": ""})

    assert response.status_code == 422


def test_autocomplete_api_failure_returns_502(monkeypatch):
    _patch_places(monkeypatch, error=GooglePlacesApiError("Google Places API returned 403."))

    response = client.get("/api/places/autocomplete", params={"input": "dfw"})

    assert response.status_code == 502
    assert response.json() == {"detail": "Could not reach the places service."}


def test_autocomplete_no_suggestions_returns_empty_list(monkeypatch):
    _patch_places(monkeypatch, suggestions=[])

    response = client.get("/api/places/autocomplete", params={"input": "asdkfjhaslkdjfh"})

    assert response.status_code == 200
    assert response.json() == []


def test_autocomplete_api_key_never_appears_in_response(monkeypatch):
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "super-secret-should-never-leak")
    _patch_places(monkeypatch, error=GooglePlacesApiError("Google Places API returned 403."))

    response = client.get("/api/places/autocomplete", params={"input": "dfw"})

    assert "super-secret-should-never-leak" not in response.text
