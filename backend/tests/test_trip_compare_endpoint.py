"""
Tests for POST /api/trips/compare. Google Routes calls are monkeypatched
at the app.routes.trips import site -- no real network calls. GTFS
matching is tested against a real temporary SQLite database, same pattern
as test_route_comparison_gtfs_context.py.
"""

import pytest
from fastapi.testclient import TestClient

from app import database
from app.clients.google_routes_client import GoogleRoutesApiError
from app.main import app
from app.repositories import gtfs_repository

client = TestClient(app)

DRIVE_RESPONSE = {"routes": [{"duration": "840s", "distanceMeters": 7724, "polyline": {"encodedPolyline": "abc"}}]}


def _body(origin="A", destination="B", origin_place_id=None, destination_place_id=None):
    origin_obj = {"label": origin}
    if origin_place_id:
        origin_obj["place_id"] = origin_place_id
    destination_obj = {"label": destination}
    if destination_place_id:
        destination_obj["place_id"] = destination_place_id
    return {"origin": origin_obj, "destination": destination_obj}


def _transit_response(agency_name: str, route_short_name: str, route_long_name: str) -> dict:
    return {
        "routes": [
            {
                "duration": "1860s",
                "distanceMeters": 8368,
                "polyline": {"encodedPolyline": "xyz"},
                "legs": [
                    {
                        "steps": [
                            {"travelMode": "WALK", "staticDuration": "300s"},
                            {
                                "travelMode": "TRANSIT",
                                "transitDetails": {
                                    "headsign": "Downtown",
                                    "transitLine": {
                                        "name": route_long_name,
                                        "nameShort": route_short_name,
                                        "agencies": [{"name": agency_name}],
                                    },
                                },
                            },
                        ]
                    }
                ],
            }
        ]
    }


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "trip_compare.db")
    database.init_db()


@pytest.fixture
def seeded_dart_route(temp_db):
    gtfs_repository.insert_agencies([("DART", "1", "DALLAS AREA RAPID TRANSIT", "http://dart.example", "America/Chicago")])
    gtfs_repository.insert_routes([("DART", "27243", "1", "620", "DALLAS STREETCAR", "0")])
    gtfs_repository.insert_calendar([("DART", "WD", 1, 1, 1, 1, 1, 1, 1, "20200101", "20301231")])
    gtfs_repository.insert_trips(
        [
            ("DART", "T1", "27243", "WD", "Downtown", "0", None),
            ("DART", "T2", "27243", "WD", "Downtown", "0", None),
        ]
    )
    gtfs_repository.insert_stop_times(
        [
            ("DART", "T1", "S1", "08:00:00", "08:00:00", 1),
            ("DART", "T2", "S1", "08:20:00", "08:20:00", 1),
        ]
    )


def _patch_google(monkeypatch, drive=None, transit=None, drive_error=None, transit_error=None):
    import app.routes.trips as trips_module

    def fake_drive(origin, destination):
        if drive_error:
            raise drive_error
        return drive

    def fake_transit(origin, destination, departure_time):
        if transit_error:
            raise transit_error
        return transit

    monkeypatch.setattr(trips_module, "fetch_drive_route", fake_drive)
    monkeypatch.setattr(trips_module, "fetch_transit_route", fake_transit)


def test_compare_trip_matches_gtfs_route_and_returns_full_response(seeded_dart_route, monkeypatch):
    _patch_google(
        monkeypatch,
        drive=DRIVE_RESPONSE,
        transit=_transit_response("DALLAS AREA RAPID TRANSIT", "620", "DALLAS STREETCAR"),
    )

    response = client.post(
        "/api/trips/compare", json=_body("Bishop Arts, Dallas, TX", "Downtown Dallas, TX")
    )

    assert response.status_code == 200
    body = response.json()
    assert body["origin"] == "Bishop Arts, Dallas, TX"
    assert body["driving"]["duration_minutes"] == 14
    assert body["transit"]["duration_minutes"] == 31
    assert body["transit"]["route_names"] == ["620"]
    assert [s["travel_mode"] for s in body["transit"]["segments"]] == ["WALK", "TRANSIT"]
    assert [leg["kind"] for leg in body["transit"]["itinerary"]] == ["walk", "ride"]
    assert body["transit"]["itinerary"][1]["label"] == "620"
    assert body["comparison"]["transit_penalty"] == round(31 / 14, 2)
    assert body["comparison"]["extra_minutes"] == 17

    ctx = body["gtfs_service_context"]
    assert len(ctx) == 1
    assert ctx[0]["matched"] is True
    assert ctx[0]["agency_source"] == "DART"
    assert ctx[0]["route_id"] == "27243"
    assert ctx[0]["average_headway_minutes"] == 20.0
    assert ctx[0]["frequency_classification"] == "moderate"


def test_compare_trip_includes_representative_weekday_departure_time(seeded_dart_route, monkeypatch):
    from datetime import datetime

    _patch_google(
        monkeypatch,
        drive=DRIVE_RESPONSE,
        transit=_transit_response("DALLAS AREA RAPID TRANSIT", "620", "DALLAS STREETCAR"),
    )

    response = client.post("/api/trips/compare", json=_body())

    departure_time = datetime.fromisoformat(response.json()["departure_time"])
    assert departure_time.weekday() < 5
    assert departure_time.hour == 9


def test_compare_trip_unrecognized_agency_is_unmatched(temp_db, monkeypatch):
    _patch_google(
        monkeypatch,
        drive=DRIVE_RESPONSE,
        transit=_transit_response("Some Unknown Transit Agency", "99", "Unknown Line"),
    )

    response = client.post("/api/trips/compare", json=_body())

    assert response.status_code == 200
    ctx = response.json()["gtfs_service_context"]
    assert ctx[0]["matched"] is False
    assert ctx[0]["agency_source"] is None
    assert ctx[0]["average_headway_minutes"] is None
    assert "not recognized" in ctx[0]["unmatched_reason"]


def test_compare_trip_no_matching_route_is_unmatched(seeded_dart_route, monkeypatch):
    _patch_google(
        monkeypatch,
        drive=DRIVE_RESPONSE,
        transit=_transit_response("DALLAS AREA RAPID TRANSIT", "999", "Nonexistent Line"),
    )

    response = client.post("/api/trips/compare", json=_body())

    assert response.status_code == 200
    ctx = response.json()["gtfs_service_context"]
    assert ctx[0]["matched"] is False
    assert ctx[0]["agency_source"] == "DART"
    assert "No matching" in ctx[0]["unmatched_reason"]


def test_compare_trip_ambiguous_match_does_not_guess(temp_db, monkeypatch):
    gtfs_repository.insert_agencies([("DART", "1", "DALLAS AREA RAPID TRANSIT", "http://dart.example", None)])
    # Two different real routes sharing the same short name -- ambiguous on purpose.
    gtfs_repository.insert_routes(
        [
            ("DART", "R1", "1", "620", "DALLAS STREETCAR A", "0"),
            ("DART", "R2", "1", "620", "DALLAS STREETCAR B", "0"),
        ]
    )
    _patch_google(
        monkeypatch,
        drive=DRIVE_RESPONSE,
        transit=_transit_response("DALLAS AREA RAPID TRANSIT", "620", "DALLAS STREETCAR A"),
    )

    response = client.post("/api/trips/compare", json=_body())

    assert response.status_code == 200
    ctx = response.json()["gtfs_service_context"]
    assert ctx[0]["matched"] is False
    assert "Multiple" in ctx[0]["unmatched_reason"]


def test_compare_trip_no_transit_lines_returns_empty_gtfs_context(temp_db, monkeypatch):
    walk_only_transit = {"routes": [{"duration": "600s", "legs": [{"steps": [{"travelMode": "WALK", "staticDuration": "600s"}]}]}]}
    _patch_google(monkeypatch, drive=DRIVE_RESPONSE, transit=walk_only_transit)

    response = client.post("/api/trips/compare", json=_body())

    assert response.status_code == 200
    assert response.json()["gtfs_service_context"] == []


def test_compare_trip_google_api_failure_returns_502(temp_db, monkeypatch):
    _patch_google(monkeypatch, drive_error=GoogleRoutesApiError("Google Routes API returned 403."))

    response = client.post("/api/trips/compare", json=_body())

    assert response.status_code == 502
    assert response.json() == {"detail": "Could not reach the routing service."}


def test_compare_trip_missing_route_returns_404(temp_db, monkeypatch):
    _patch_google(monkeypatch, drive=DRIVE_RESPONSE, transit={"routes": []})

    response = client.post("/api/trips/compare", json=_body())

    assert response.status_code == 404


def test_compare_trip_malformed_response_with_zero_duration_returns_404(temp_db, monkeypatch):
    # "routes" present but missing every field this app reads -- duration
    # normalizes to 0, which can't produce a real transit penalty, so this
    # is correctly a 404 rather than a fabricated all-zeros 200.
    _patch_google(monkeypatch, drive={"routes": [{}]}, transit={"routes": [{}]})

    response = client.post("/api/trips/compare", json=_body())

    assert response.status_code == 404


def test_compare_trip_malformed_transit_legs_does_not_crash(temp_db, monkeypatch):
    # Valid driving route; transit route has a duration but no legs/steps
    # at all -- should degrade to zero walking/transfers, not crash.
    _patch_google(monkeypatch, drive=DRIVE_RESPONSE, transit={"routes": [{"duration": "900s"}]})

    response = client.post("/api/trips/compare", json=_body())

    assert response.status_code == 200
    body = response.json()
    assert body["transit"]["duration_minutes"] == 15
    assert body["transit"]["walking_minutes"] == 0
    assert body["transit"]["transfers"] == 0
    assert body["gtfs_service_context"] == []


def test_compare_trip_missing_request_fields_returns_422():
    response = client.post("/api/trips/compare", json={"origin": {"label": "A"}})

    assert response.status_code == 422


def test_compare_trip_blank_label_returns_422():
    response = client.post("/api/trips/compare", json=_body(origin="   "))

    assert response.status_code == 422


def test_compare_trip_prefers_place_id_over_label_in_google_request(temp_db, monkeypatch):
    """Leaves fetch_drive_route/fetch_transit_route real and only fakes
    httpx.post, so the actual waypoint-building code path runs."""
    import httpx

    from app import config
    from app.clients import google_routes_client as client_module

    monkeypatch.setattr(config, "get_google_maps_api_key", lambda: "fake-key")
    monkeypatch.setattr(client_module, "get_google_maps_api_key", lambda: "fake-key")

    captured_bodies = []

    def fake_post(url, json, headers, timeout):
        captured_bodies.append(json)
        return httpx.Response(200, json=DRIVE_RESPONSE, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "post", fake_post)

    client.post(
        "/api/trips/compare",
        json=_body(
            origin="DFW International Airport (display text)",
            destination="Downtown Dallas, TX",
            origin_place_id="ChIJ_dfw_airport",
        ),
    )

    assert captured_bodies[0]["origin"] == {"placeId": "ChIJ_dfw_airport"}
    assert captured_bodies[1]["destination"] == {"address": "Downtown Dallas, TX"}


def test_api_key_never_appears_in_any_response(temp_db, monkeypatch):
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "super-secret-should-never-leak")
    _patch_google(monkeypatch, drive_error=GoogleRoutesApiError("Google Routes API returned 403."))

    response = client.post("/api/trips/compare", json=_body())

    assert "super-secret-should-never-leak" not in response.text


def test_api_key_never_appears_end_to_end_through_real_client(temp_db, monkeypatch):
    """Unlike the other key tests, this leaves fetch_drive_route/fetch_transit_route
    real and only fakes httpx.post, so the actual client code path runs."""
    import httpx

    from app import config
    from app.clients import google_routes_client as client_module

    monkeypatch.setattr(config, "get_google_maps_api_key", lambda: "super-secret-should-never-leak")
    monkeypatch.setattr(client_module, "get_google_maps_api_key", lambda: "super-secret-should-never-leak")

    def fake_post(url, json, headers, timeout):
        return httpx.Response(403, json={"error": "forbidden"}, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "post", fake_post)

    response = client.post("/api/trips/compare", json=_body())

    assert response.status_code == 502
    assert "super-secret-should-never-leak" not in response.text


def test_api_key_never_appears_in_successful_response(seeded_dart_route, monkeypatch):
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "super-secret-should-never-leak")
    _patch_google(
        monkeypatch,
        drive=DRIVE_RESPONSE,
        transit=_transit_response("DALLAS AREA RAPID TRANSIT", "620", "DALLAS STREETCAR"),
    )

    response = client.post("/api/trips/compare", json=_body())

    assert response.status_code == 200
    assert "super-secret-should-never-leak" not in response.text
