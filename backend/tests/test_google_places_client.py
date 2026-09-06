"""
Tests for app/clients/google_places_client.py. No real network calls --
httpx.post is monkeypatched throughout.
"""

import httpx
import pytest

from app import config
from app.clients import google_places_client as client_module
from app.clients.google_places_client import GooglePlacesApiError, fetch_autocomplete_suggestions

FAKE_API_KEY = "fake-test-key-should-never-appear-in-errors"


@pytest.fixture
def with_api_key(monkeypatch):
    monkeypatch.setattr(config, "get_google_maps_api_key", lambda: FAKE_API_KEY)
    monkeypatch.setattr(client_module, "get_google_maps_api_key", lambda: FAKE_API_KEY)


def test_missing_api_key_raises_without_making_a_request(monkeypatch):
    monkeypatch.setattr(client_module, "get_google_maps_api_key", lambda: None)

    def _unexpected_post(*args, **kwargs):
        raise AssertionError("httpx.post should not be called when the API key is missing")

    monkeypatch.setattr(httpx, "post", _unexpected_post)

    with pytest.raises(GooglePlacesApiError):
        fetch_autocomplete_suggestions("dfw")


def test_fetch_autocomplete_suggestions_calls_both_city_biases(with_api_key, monkeypatch):
    captured = []

    def fake_post(url, json, headers, timeout):
        captured.append(json)
        return httpx.Response(200, json={"suggestions": []}, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "post", fake_post)

    fetch_autocomplete_suggestions("dfw")

    assert len(captured) == 2
    centers = {call["locationBias"]["circle"]["center"]["latitude"] for call in captured}
    assert client_module.DALLAS_BIAS["latitude"] in centers
    assert client_module.CHICAGO_BIAS["latitude"] in centers
    for call in captured:
        assert call["input"] == "dfw"


def test_fetch_autocomplete_suggestions_concatenates_both_calls(with_api_key, monkeypatch):
    dallas_suggestion = {"placePrediction": {"placeId": "dallas-1"}}
    chicago_suggestion = {"placePrediction": {"placeId": "chicago-1"}}
    call_count = {"n": 0}

    def fake_post(url, json, headers, timeout):
        call_count["n"] += 1
        body = {"suggestions": [dallas_suggestion]} if call_count["n"] == 1 else {"suggestions": [chicago_suggestion]}
        return httpx.Response(200, json=body, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "post", fake_post)

    results = fetch_autocomplete_suggestions("main st")

    assert results == [dallas_suggestion, chicago_suggestion]


def test_http_error_status_raises_google_places_api_error(with_api_key, monkeypatch):
    def fake_post(url, json, headers, timeout):
        return httpx.Response(403, json={"error": "forbidden"}, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "post", fake_post)

    with pytest.raises(GooglePlacesApiError):
        fetch_autocomplete_suggestions("dfw")


def test_network_error_raises_google_places_api_error(with_api_key, monkeypatch):
    def fake_post(url, json, headers, timeout):
        raise httpx.ConnectTimeout("timed out")

    monkeypatch.setattr(httpx, "post", fake_post)

    with pytest.raises(GooglePlacesApiError):
        fetch_autocomplete_suggestions("dfw")


def test_api_key_never_appears_in_error_message(with_api_key, monkeypatch):
    def fake_post(url, json, headers, timeout):
        return httpx.Response(403, json={"error": "forbidden"}, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "post", fake_post)

    with pytest.raises(GooglePlacesApiError) as excinfo:
        fetch_autocomplete_suggestions("dfw")

    assert FAKE_API_KEY not in str(excinfo.value)
