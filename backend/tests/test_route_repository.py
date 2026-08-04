"""
Tests for the SQLite repository layer.

Each test points app.database at a fresh temporary file (via monkeypatch),
so these tests never touch the real backend/transit_lab.db.
"""

import pytest

from app import database
from app.repositories import route_repository
from app.schemas import RouteScenario

DALLAS_ROUTE = RouteScenario(
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
    notes="Manual V1 sample estimate; verify before research use.",
)

CHICAGO_ROUTE = RouteScenario(
    id=2,
    city="Chicago",
    origin_label="Hyde Park",
    destination_label="The Loop",
    route_category="campus_to_downtown",
    time_period="weekday_morning",
    distance_miles=7.8,
    driving_minutes=24,
    transit_minutes=42,
    walking_minutes=8,
    wait_transfer_minutes=12,
    transfers=1,
    fare_cost=2.5,
    gas_cost=2.1,
    driving_emissions_kg=3.1,
    transit_emissions_kg=0.8,
    notes="Manual V1 sample estimate; verify before research use.",
)


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "test.db")
    database.init_db()


def test_replace_all_routes_then_list_routes(temp_db):
    route_repository.replace_all_routes([DALLAS_ROUTE, CHICAGO_ROUTE])

    routes = route_repository.list_routes()

    assert len(routes) == 2
    assert {route.id for route in routes} == {1, 2}


def test_replace_all_routes_is_idempotent(temp_db):
    route_repository.replace_all_routes([DALLAS_ROUTE, CHICAGO_ROUTE])
    route_repository.replace_all_routes([DALLAS_ROUTE, CHICAGO_ROUTE])

    routes = route_repository.list_routes()

    assert len(routes) == 2


def test_list_routes_filters_by_city_case_insensitively(temp_db):
    route_repository.replace_all_routes([DALLAS_ROUTE, CHICAGO_ROUTE])

    routes = route_repository.list_routes(city="dallas")

    assert len(routes) == 1
    assert routes[0].id == DALLAS_ROUTE.id


def test_get_route_by_id_found(temp_db):
    route_repository.replace_all_routes([DALLAS_ROUTE, CHICAGO_ROUTE])

    route = route_repository.get_route_by_id(2)

    assert route is not None
    assert route.origin_label == "Hyde Park"


def test_get_route_by_id_missing_returns_none(temp_db):
    route_repository.replace_all_routes([DALLAS_ROUTE])

    assert route_repository.get_route_by_id(999) is None
