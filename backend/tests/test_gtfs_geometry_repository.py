"""
Tests for gtfs_geometry_repository.py, against a temporary SQLite file
seeded directly through gtfs_repository's insert_* functions.
"""

import pytest

from app import database
from app.repositories import gtfs_geometry_repository, gtfs_repository


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "test.db")
    database.init_db()


def test_find_representative_shape_id_single_shape(temp_db):
    gtfs_repository.insert_trips([("CTA", "T1", "R1", "WD", "Downtown", "0", "SHP1")])

    assert gtfs_geometry_repository.find_representative_shape_id("CTA", "R1") == "SHP1"


def test_find_representative_shape_id_picks_most_used_shape(temp_db):
    # SHP_A has 2 trips, SHP_B has 1 -- SHP_A should win.
    gtfs_repository.insert_trips(
        [
            ("CTA", "T1", "R1", "WD", "Downtown", "0", "SHP_A"),
            ("CTA", "T2", "R1", "WD", "Downtown", "0", "SHP_A"),
            ("CTA", "T3", "R1", "WD", "Downtown", "1", "SHP_B"),
        ]
    )

    assert gtfs_geometry_repository.find_representative_shape_id("CTA", "R1") == "SHP_A"


def test_find_representative_shape_id_ties_break_alphabetically(temp_db):
    # Both shapes used by exactly one trip -- deterministic tie-break picks
    # the alphabetically-first shape_id, so re-imports don't flip the choice.
    gtfs_repository.insert_trips(
        [
            ("CTA", "T1", "R1", "WD", "Downtown", "0", "SHP_Z"),
            ("CTA", "T2", "R1", "WD", "Downtown", "1", "SHP_A"),
        ]
    )

    assert gtfs_geometry_repository.find_representative_shape_id("CTA", "R1") == "SHP_A"


def test_find_representative_shape_id_ignores_null_and_empty_shape_ids(temp_db):
    gtfs_repository.insert_trips(
        [
            ("CTA", "T1", "R1", "WD", "Downtown", "0", None),
            ("CTA", "T2", "R1", "WD", "Downtown", "0", ""),
        ]
    )

    assert gtfs_geometry_repository.find_representative_shape_id("CTA", "R1") is None


def test_find_representative_shape_id_route_with_no_trips_returns_none(temp_db):
    assert gtfs_geometry_repository.find_representative_shape_id("CTA", "NOPE") is None


def test_find_representative_shape_id_is_agency_isolated(temp_db):
    # Same route_id and shape_id text reused across agencies on purpose --
    # each is only guaranteed unique within one agency's own feed.
    gtfs_repository.insert_trips(
        [
            ("CTA", "T1", "R1", "WD", "Downtown", "0", "SHP1"),
            ("DART", "T1", "R1", "WD", "Downtown", "0", "SHP2"),
        ]
    )

    assert gtfs_geometry_repository.find_representative_shape_id("CTA", "R1") == "SHP1"
    assert gtfs_geometry_repository.find_representative_shape_id("DART", "R1") == "SHP2"


def test_get_shape_points_returns_ordered_by_sequence(temp_db):
    gtfs_repository.insert_shapes(
        [
            ("CTA", "SHP1", 41.9, -87.6, 2, 100.0),
            ("CTA", "SHP1", 41.8, -87.7, 1, 0.0),
            ("CTA", "SHP1", 42.0, -87.5, 3, 200.0),
        ]
    )

    points = gtfs_geometry_repository.get_shape_points("CTA", "SHP1")

    assert [p["shape_pt_sequence"] for p in points] == [1, 2, 3]
    assert points[0]["shape_pt_lat"] == 41.8


def test_get_shape_points_missing_dist_traveled_is_none(temp_db):
    gtfs_repository.insert_shapes([("CTA", "SHP1", 41.8, -87.7, 1, None)])

    points = gtfs_geometry_repository.get_shape_points("CTA", "SHP1")

    assert points[0]["shape_dist_traveled"] is None


def test_get_shape_points_unknown_shape_returns_empty_list(temp_db):
    assert gtfs_geometry_repository.get_shape_points("CTA", "NOPE") == []


def test_get_shape_points_is_agency_isolated(temp_db):
    # Same shape_id text reused across agencies with different points.
    gtfs_repository.insert_shapes(
        [
            ("CTA", "SHP1", 41.8, -87.7, 1, None),
            ("DART", "SHP1", 32.8, -96.8, 1, None),
        ]
    )

    cta_points = gtfs_geometry_repository.get_shape_points("CTA", "SHP1")
    dart_points = gtfs_geometry_repository.get_shape_points("DART", "SHP1")

    assert cta_points[0]["shape_pt_lat"] == 41.8
    assert dart_points[0]["shape_pt_lat"] == 32.8
