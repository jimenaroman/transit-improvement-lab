"""
Tests for the gtfs_service_context field on GET /api/routes/{route_id}/comparison.

Pre-existing comparison fields (current_metrics, recommended_improvement)
are already covered by test_scoring.py and test_simulator.py -- these
tests focus on what's new: the GTFS bridge, not the underlying scoring
math.
"""

import pytest
from fastapi.testclient import TestClient

from app import database
from app.main import app
from app.repositories import gtfs_repository, route_repository, scenario_gtfs_link_repository
from app.schemas import RouteScenario

client = TestClient(app)

LINKED_SCENARIO = RouteScenario(
    id=1,
    city="Dallas",
    origin_label="Bishop Arts",
    destination_label="Downtown Dallas",
    route_category="neighborhood_to_downtown",
    time_period="weekday_morning",
    distance_miles=3.4,
    driving_minutes=12,
    transit_minutes=29,
    walking_minutes=8,
    wait_transfer_minutes=9,
    transfers=1,
    fare_cost=2.5,
    gas_cost=0.85,
    driving_emissions_kg=1.4,
    transit_emissions_kg=0.5,
    notes="Manual V1 sample estimate; verify before research use.",
)

UNLINKED_SCENARIO = LINKED_SCENARIO.model_copy(update={"id": 2, "origin_label": "Oak Cliff"})


@pytest.fixture
def seeded_comparison_data(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "test.db")
    database.init_db()
    route_repository.replace_all_routes([LINKED_SCENARIO, UNLINKED_SCENARIO])

    # CTA route "6", active every day of the week, two trips 20 min apart -> "moderate".
    gtfs_repository.insert_routes([("CTA", "6", "1", "6", "Jackson Park Express", "3")])
    gtfs_repository.insert_calendar([("CTA", "WD", 1, 1, 1, 1, 1, 1, 1, "20200101", "20301231")])
    gtfs_repository.insert_trips(
        [
            ("CTA", "CT1", "6", "WD", "Downtown", "0"),
            ("CTA", "CT2", "6", "WD", "Downtown", "0"),
        ]
    )
    gtfs_repository.insert_stop_times(
        [
            ("CTA", "CT1", "S1", "08:00:00", "08:00:00", 1),
            ("CTA", "CT2", "S1", "08:20:00", "08:20:00", 1),
        ]
    )

    # DART route "27243", active every day of the week, two trips 45 min apart -> "infrequent".
    gtfs_repository.insert_routes([("DART", "27243", "1", "620", "DALLAS STREETCAR", "5")])
    gtfs_repository.insert_calendar([("DART", "WD", 1, 1, 1, 1, 1, 1, 1, "20200101", "20301231")])
    gtfs_repository.insert_trips(
        [
            ("DART", "DT1", "27243", "WD", "Downtown", "0"),
            ("DART", "DT2", "27243", "WD", "Downtown", "0"),
        ]
    )
    gtfs_repository.insert_stop_times(
        [
            ("DART", "DT1", "S1", "07:00:00", "07:00:00", 1),
            ("DART", "DT2", "S1", "07:45:00", "07:45:00", 1),
        ]
    )

    scenario_gtfs_link_repository.replace_links_for_scenario(
        1,
        [
            {"agency_source": "CTA", "route_id": "6", "role": "primary"},
            {"agency_source": "DART", "route_id": "27243", "role": "secondary"},
        ],
    )


def test_linked_scenario_returns_gtfs_service_context(seeded_comparison_data):
    response = client.get("/api/routes/1/comparison?date=2026-08-11")

    assert response.status_code == 200
    body = response.json()
    assert len(body["gtfs_service_context"]) == 2


def test_unlinked_scenario_returns_original_comparison_with_empty_context(seeded_comparison_data):
    response = client.get("/api/routes/2/comparison")

    assert response.status_code == 200
    body = response.json()
    assert body["gtfs_service_context"] == []
    # The rest of the comparison still works normally.
    assert "current_metrics" in body
    assert "recommended_improvement" in body


def test_cta_and_dart_links_do_not_mix(seeded_comparison_data):
    response = client.get("/api/routes/1/comparison?date=2026-08-11")

    body = response.json()
    by_agency = {ctx["agency_source"]: ctx for ctx in body["gtfs_service_context"]}

    assert by_agency["CTA"]["route_id"] == "6"
    assert by_agency["CTA"]["frequency_classification"] == "moderate"  # 20 min headway
    assert by_agency["CTA"]["role"] == "primary"

    assert by_agency["DART"]["route_id"] == "27243"
    assert by_agency["DART"]["frequency_classification"] == "infrequent"  # 45 min headway
    assert by_agency["DART"]["role"] == "secondary"


def test_explicit_date_propagates_into_gtfs_calculations(seeded_comparison_data):
    # Add a second calendar pattern for CTA "6" that's Tuesday-only, with a
    # different, distinguishable headway, plus a calendar_dates removal of
    # the always-on "WD" pattern for that one Tuesday -- so the date
    # actually changes which trips are active, not just the label.
    gtfs_repository.insert_calendar([("CTA", "TUE_ONLY", 0, 1, 0, 0, 0, 0, 0, "20200101", "20301231")])
    gtfs_repository.insert_trips([("CTA", "CT3", "6", "TUE_ONLY", "Downtown", "0")])
    gtfs_repository.insert_stop_times([("CTA", "CT3", "S1", "09:00:00", "09:00:00", 1)])
    gtfs_repository.insert_calendar_dates([("CTA", "WD", "20260811", "2")])

    tuesday_response = client.get("/api/routes/1/comparison?date=2026-08-11").json()
    other_day_response = client.get("/api/routes/1/comparison?date=2026-08-12").json()

    cta_tuesday = next(ctx for ctx in tuesday_response["gtfs_service_context"] if ctx["agency_source"] == "CTA")
    cta_other_day = next(ctx for ctx in other_day_response["gtfs_service_context"] if ctx["agency_source"] == "CTA")

    assert cta_tuesday["service_date"] == "2026-08-11"
    assert cta_tuesday["average_headway_minutes"] is None  # only one TUE_ONLY trip that day -> null headway
    assert cta_tuesday["frequency_classification"] == "minimal"
    assert cta_other_day["service_date"] == "2026-08-12"
    assert cta_other_day["average_headway_minutes"] == 20.0  # back to the normal "WD" pattern


def test_unknown_scenario_still_returns_404(seeded_comparison_data):
    response = client.get("/api/routes/999/comparison")

    assert response.status_code == 404


def test_existing_comparison_metrics_are_unchanged(seeded_comparison_data):
    response = client.get("/api/routes/2/comparison")  # unlinked scenario, no GTFS noise

    body = response.json()
    assert body["route"]["id"] == 2
    assert body["current_metrics"]["transit_penalty"] == round(29 / 12, 2)
    assert "car_dependency_score" in body["current_metrics"]
    assert "weekly_extra_transit_hours" in body["current_metrics"]
    assert "emissions_saved_kg" in body["current_metrics"]
    assert body["recommended_improvement"]["title"]
    assert body["recommended_improvement"]["verdict"]
