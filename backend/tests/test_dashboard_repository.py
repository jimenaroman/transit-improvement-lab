"""
Tests for the dashboard aggregate queries.

Uses the same temp-database pattern as test_route_repository.py, seeded
with three routes whose transit penalties and wait times are picked by
hand so the expected aggregates can be worked out on paper:

  Route 1 (Dallas, suburb_to_downtown):  91 / 28 min -> penalty 3.25, wait 34
  Route 2 (Dallas, suburb_to_downtown):  40 / 20 min -> penalty 2.00, wait 10
  Route 3 (Chicago, campus_to_downtown): 42 / 24 min -> penalty 1.75, wait 12
"""

import pytest

from app import database
from app.repositories import dashboard_repository, route_repository
from app.schemas import RouteScenario

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
    notes="Manual V1 sample estimate; verify before research use.",
)

ROUTE_2 = RouteScenario(
    id=2,
    city="Dallas",
    origin_label="Richardson",
    destination_label="Downtown Dallas",
    route_category="suburb_to_downtown",
    time_period="weekday_morning",
    distance_miles=17.5,
    driving_minutes=20,
    transit_minutes=40,
    walking_minutes=10,
    wait_transfer_minutes=10,
    transfers=0,
    fare_cost=3.0,
    gas_cost=4.3,
    driving_emissions_kg=7.1,
    transit_emissions_kg=1.6,
    notes="Manual V1 sample estimate; verify before research use.",
)

ROUTE_3 = RouteScenario(
    id=3,
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
def seeded_db(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "test.db")
    database.init_db()
    route_repository.replace_all_routes([ROUTE_1, ROUTE_2, ROUTE_3])


@pytest.fixture
def empty_db(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "empty.db")
    database.init_db()


def test_count_routes(seeded_db):
    assert dashboard_repository.count_routes() == 3


def test_average_transit_penalty(seeded_db):
    # (3.25 + 2.00 + 1.75) / 3 = 2.333...
    assert dashboard_repository.average_transit_penalty() == pytest.approx(2.33, abs=0.01)


def test_average_transit_penalty_by_city(seeded_db):
    by_city = {row.city: row.average_transit_penalty for row in dashboard_repository.average_transit_penalty_by_city()}

    assert by_city["Dallas"] == pytest.approx(2.625, abs=0.01)  # (3.25 + 2.00) / 2
    assert by_city["Chicago"] == pytest.approx(1.75, abs=0.01)


def test_average_wait_transfer_minutes_by_city(seeded_db):
    by_city = {
        row.city: row.average_wait_transfer_minutes
        for row in dashboard_repository.average_wait_transfer_minutes_by_city()
    }

    assert by_city["Dallas"] == 22.0  # (34 + 10) / 2
    assert by_city["Chicago"] == 12.0


def test_worst_route_by_transit_penalty(seeded_db):
    worst = dashboard_repository.worst_route_by_transit_penalty()

    assert worst is not None
    assert worst.id == 1
    assert worst.transit_penalty == pytest.approx(3.25)


def test_worst_route_by_wait_transfer_minutes(seeded_db):
    worst = dashboard_repository.worst_route_by_wait_transfer_minutes()

    assert worst is not None
    assert worst.id == 1
    assert worst.wait_transfer_minutes == 34


def test_route_count_by_category(seeded_db):
    counts = {row.route_category: row.count for row in dashboard_repository.route_count_by_category()}

    assert counts["suburb_to_downtown"] == 2
    assert counts["campus_to_downtown"] == 1


def test_get_summary_on_empty_database(empty_db):
    summary = dashboard_repository.get_summary()

    assert summary.total_routes == 0
    assert summary.average_transit_penalty == 0.0
    assert summary.worst_route_by_transit_penalty is None
    assert summary.worst_route_by_wait_transfer_minutes is None
    assert summary.average_transit_penalty_by_city == []
    assert summary.route_count_by_category == []
