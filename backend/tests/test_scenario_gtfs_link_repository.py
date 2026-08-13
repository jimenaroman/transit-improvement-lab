"""
Tests for scenario_gtfs_link_repository.py, against a temporary SQLite
file seeded directly through route_repository/gtfs_repository's insert
functions.
"""

import sqlite3

import pytest

from app import database
from app.repositories import gtfs_repository, route_repository, scenario_gtfs_link_repository
from app.schemas import RouteScenario

SCENARIO_1 = RouteScenario(
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

SCENARIO_2 = SCENARIO_1.model_copy(update={"id": 2, "origin_label": "Oak Cliff"})


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "test.db")
    database.init_db()
    route_repository.replace_all_routes([SCENARIO_1, SCENARIO_2])
    gtfs_repository.insert_routes(
        [
            ("DART", "27243", "1", "620", "DALLAS STREETCAR", "5"),
            ("CTA", "6", "1", "6", "Jackson Park Express", "3"),
        ]
    )


def test_scenario_exists(temp_db):
    assert scenario_gtfs_link_repository.scenario_exists(1) is True
    assert scenario_gtfs_link_repository.scenario_exists(999) is False


def test_route_exists(temp_db):
    assert scenario_gtfs_link_repository.route_exists("DART", "27243") is True
    assert scenario_gtfs_link_repository.route_exists("dart", "27243") is True  # case-insensitive agency
    assert scenario_gtfs_link_repository.route_exists("DART", "NOPE") is False
    assert scenario_gtfs_link_repository.route_exists("CTA", "27243") is False  # wrong agency for this route


def test_replace_links_for_scenario_then_list(temp_db):
    scenario_gtfs_link_repository.replace_links_for_scenario(
        1, [{"agency_source": "DART", "route_id": "27243", "role": "primary"}]
    )

    links = scenario_gtfs_link_repository.list_links_for_scenario(1)

    assert links == [{"agency_source": "DART", "route_id": "27243", "role": "primary"}]


def test_replace_links_is_idempotent_not_additive(temp_db):
    link = {"agency_source": "DART", "route_id": "27243", "role": "primary"}

    scenario_gtfs_link_repository.replace_links_for_scenario(1, [link])
    scenario_gtfs_link_repository.replace_links_for_scenario(1, [link])

    assert len(scenario_gtfs_link_repository.list_links_for_scenario(1)) == 1


def test_replace_links_returns_only_requested_scenarios_routes(temp_db):
    scenario_gtfs_link_repository.replace_links_for_scenario(
        1, [{"agency_source": "DART", "route_id": "27243", "role": "primary"}]
    )
    scenario_gtfs_link_repository.replace_links_for_scenario(
        2, [{"agency_source": "CTA", "route_id": "6", "role": "primary"}]
    )

    scenario_1_links = scenario_gtfs_link_repository.list_links_for_scenario(1)
    scenario_2_links = scenario_gtfs_link_repository.list_links_for_scenario(2)

    assert scenario_1_links == [{"agency_source": "DART", "route_id": "27243", "role": "primary"}]
    assert scenario_2_links == [{"agency_source": "CTA", "route_id": "6", "role": "primary"}]


def test_list_links_for_unlinked_scenario_returns_empty_list(temp_db):
    assert scenario_gtfs_link_repository.list_links_for_scenario(1) == []


def test_role_is_optional(temp_db):
    scenario_gtfs_link_repository.replace_links_for_scenario(
        1, [{"agency_source": "DART", "route_id": "27243"}]
    )

    links = scenario_gtfs_link_repository.list_links_for_scenario(1)

    assert links == [{"agency_source": "DART", "route_id": "27243", "role": None}]


def test_duplicate_association_in_one_call_is_rejected(temp_db):
    duplicate_links = [
        {"agency_source": "DART", "route_id": "27243", "role": "primary"},
        {"agency_source": "DART", "route_id": "27243", "role": "alternative"},
    ]

    with pytest.raises(sqlite3.IntegrityError):
        scenario_gtfs_link_repository.replace_links_for_scenario(1, duplicate_links)
