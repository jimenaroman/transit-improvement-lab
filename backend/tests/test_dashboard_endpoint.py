"""
Tests for GET /api/dashboard/research, using FastAPI's TestClient.

Aggregation/correlation math itself is covered in test_research_analysis.py
-- these tests check the HTTP layer: status code, JSON shape, and the
empty-database case.
"""

import pytest
from fastapi.testclient import TestClient

from app import database
from app.main import app
from app.repositories import route_repository
from app.schemas import RouteScenario

client = TestClient(app)

ROUTE_1 = RouteScenario(
    id=1,
    city="Dallas",
    origin_label="Dallas suburb",
    destination_label="Downtown Dallas",
    route_category="suburb_to_downtown",
    time_period="weekday_morning",
    distance_miles=15.2,
    driving_minutes=28,
    transit_minutes=91,
    walking_minutes=14,
    wait_transfer_minutes=34,
    transfers=2,
    fare_cost=3.0,
    gas_cost=3.75,
    driving_emissions_kg=6.2,
    transit_emissions_kg=1.4,
    notes="",
)


@pytest.fixture
def seeded_db(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "test.db")
    database.init_db()
    route_repository.replace_all_routes([ROUTE_1])


@pytest.fixture
def empty_db(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "empty.db")
    database.init_db()


def test_research_endpoint_returns_scenario_and_aggregates(seeded_db):
    response = client.get("/api/dashboard/research")

    assert response.status_code == 200
    body = response.json()
    assert body["scenario_count"] == 1
    assert body["scenarios"][0]["id"] == 1
    assert body["scenarios"][0]["transit_penalty"] == 3.25
    assert body["average_transit_penalty_by_city"] == [{"city": "Dallas", "average_transit_penalty": 3.25}]
    assert "correlations" in body
    assert body["scenarios"][0]["bottleneck_category"] == "transfer_burden"  # ROUTE_1 has 2 transfers
    assert body["bottleneck_distribution"] == [{"category": "transfer_burden", "count": 1}]


def test_research_endpoint_empty_database(empty_db):
    response = client.get("/api/dashboard/research")

    assert response.status_code == 200
    body = response.json()
    assert body["scenario_count"] == 0
    assert body["scenarios"] == []
    assert body["correlations"]["walking_minutes_vs_transit_penalty"] is None
