"""
Tests for app/clients/google_routes_client.py. No real network calls --
httpx.post is monkeypatched throughout.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

import httpx
import pytest

from app import config
from app.clients import google_routes_client as client_module
from app.clients.google_routes_client import GoogleRoutesApiError, fetch_drive_route, fetch_transit_route
from app.trip_compare_schemas import LocationInput

FAKE_API_KEY = "fake-test-key-should-never-appear-in-errors"
ORIGIN = LocationInput(label="Bishop Arts, Dallas, TX")
DESTINATION = LocationInput(label="Downtown Dallas, TX")
DEPARTURE = datetime(2026, 9, 8, 9, 0, tzinfo=ZoneInfo("America/Chicago"))


@pytest.fixture
def with_api_key(monkeypatch):
    monkeypatch.setattr(config, "get_google_maps_api_key", lambda: FAKE_API_KEY)
    monkeypatch.setattr(client_module, "get_google_maps_api_key", lambda: FAKE_API_KEY)


def _fake_response(url, body):
    return httpx.Response(200, json=body, request=httpx.Request("POST", url))


def test_missing_api_key_raises_without_making_a_request(monkeypatch):
    monkeypatch.setattr(client_module, "get_google_maps_api_key", lambda: None)

    def _unexpected_post(*args, **kwargs):
        raise AssertionError("httpx.post should not be called when the API key is missing")

    monkeypatch.setattr(httpx, "post", _unexpected_post)

    with pytest.raises(GoogleRoutesApiError):
        fetch_drive_route(ORIGIN, DESTINATION)


def test_fetch_drive_route_uses_address_and_no_departure_time(with_api_key, monkeypatch):
    captured = {}

    def fake_post(url, json, headers, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        return _fake_response(url, {"routes": [{"duration": "600s"}]})

    monkeypatch.setattr(httpx, "post", fake_post)

    fetch_drive_route(ORIGIN, DESTINATION)

    assert captured["url"] == client_module.COMPUTE_ROUTES_URL
    assert captured["json"]["travelMode"] == "DRIVE"
    assert captured["json"]["routingPreference"] == "TRAFFIC_UNAWARE"
    assert captured["json"]["origin"] == {"address": "Bishop Arts, Dallas, TX"}
    assert "departureTime" not in captured["json"]
    assert captured["headers"]["X-Goog-Api-Key"] == FAKE_API_KEY
    assert "distanceMeters" in captured["headers"]["X-Goog-FieldMask"]


def test_fetch_drive_route_prefers_place_id_over_label(with_api_key, monkeypatch):
    captured = {}

    def fake_post(url, json, headers, timeout):
        captured["json"] = json
        return _fake_response(url, {"routes": [{"duration": "600s"}]})

    monkeypatch.setattr(httpx, "post", fake_post)

    origin_with_place_id = LocationInput(label="DFW Airport (display text)", place_id="ChIJabc123")
    fetch_drive_route(origin_with_place_id, DESTINATION)

    assert captured["json"]["origin"] == {"placeId": "ChIJabc123"}


def test_fetch_transit_route_uses_transit_mode_and_sends_departure_time(with_api_key, monkeypatch):
    captured = {}

    def fake_post(url, json, headers, timeout):
        captured["json"] = json
        return _fake_response(url, {"routes": [{"duration": "1200s"}]})

    monkeypatch.setattr(httpx, "post", fake_post)

    fetch_transit_route(ORIGIN, DESTINATION, DEPARTURE)

    assert captured["json"]["travelMode"] == "TRANSIT"
    assert "routingPreference" not in captured["json"]
    assert captured["json"]["departureTime"] == DEPARTURE.isoformat()


def test_fetch_transit_route_requests_per_step_polyline(with_api_key, monkeypatch):
    captured = {}

    def fake_post(url, json, headers, timeout):
        captured["headers"] = headers
        return _fake_response(url, {"routes": [{"duration": "1200s"}]})

    monkeypatch.setattr(httpx, "post", fake_post)

    fetch_transit_route(ORIGIN, DESTINATION, DEPARTURE)

    # Needed so the map can color-code walk vs. transit segments.
    assert "routes.legs.steps.polyline.encodedPolyline" in captured["headers"]["X-Goog-FieldMask"]


def test_http_error_status_raises_google_routes_api_error(with_api_key, monkeypatch):
    def fake_post(url, json, headers, timeout):
        return httpx.Response(403, json={"error": "forbidden"}, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "post", fake_post)

    with pytest.raises(GoogleRoutesApiError):
        fetch_drive_route(ORIGIN, DESTINATION)


def test_network_error_raises_google_routes_api_error(with_api_key, monkeypatch):
    def fake_post(url, json, headers, timeout):
        raise httpx.ConnectTimeout("timed out")

    monkeypatch.setattr(httpx, "post", fake_post)

    with pytest.raises(GoogleRoutesApiError):
        fetch_drive_route(ORIGIN, DESTINATION)


def test_non_json_response_raises_google_routes_api_error(with_api_key, monkeypatch):
    def fake_post(url, json, headers, timeout):
        return httpx.Response(200, text="not json", request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "post", fake_post)

    with pytest.raises(GoogleRoutesApiError):
        fetch_drive_route(ORIGIN, DESTINATION)


def test_api_key_never_appears_in_error_message(with_api_key, monkeypatch):
    def fake_post(url, json, headers, timeout):
        return httpx.Response(403, json={"error": "forbidden"}, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "post", fake_post)

    with pytest.raises(GoogleRoutesApiError) as excinfo:
        fetch_drive_route(ORIGIN, DESTINATION)

    assert FAKE_API_KEY not in str(excinfo.value)
