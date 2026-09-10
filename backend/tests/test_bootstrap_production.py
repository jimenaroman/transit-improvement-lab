"""
Tests for app/bootstrap_production.py.

Uses the same hand-written tiny GTFS zip fixture as test_import_gtfs.py --
never the real multi-million-row CTA/DART feeds -- so these stay fast. The
curated trip_scenarios/scenario-gtfs-links JSON files are the real (tiny)
project data, not test doubles, since seeding them is exactly what this
command does in production.
"""

import zipfile

import pytest

from app import bootstrap_production, database
from app.repositories import gtfs_repository, route_repository

AGENCY_TXT = "agency_id,agency_name,agency_url,agency_timezone\n1,Test Transit,http://example.com,America/Chicago\n"
ROUTES_TXT = "route_id,agency_id,route_short_name,route_long_name,route_type\nR1,1,1,Test Route One,3\n"
STOPS_TXT = "stop_id,stop_name,stop_lat,stop_lon\nS1,First Stop,41.8,-87.6\nS2,Second Stop,41.9,-87.7\n"
TRIPS_TXT = "route_id,service_id,trip_id,direction_id,shape_id\nR1,WD,T1,0,SHP1\n"
SHAPES_TXT = (
    "shape_id,shape_pt_lat,shape_pt_lon,shape_pt_sequence,shape_dist_traveled\n"
    "SHP1,41.80,-87.60,1,0\nSHP1,41.85,-87.65,2,0.5\n"
)
STOP_TIMES_TXT = (
    "trip_id,arrival_time,departure_time,stop_id,stop_sequence\nT1,08:00:00,08:00:00,S1,1\nT1,08:05:00,08:05:00,S2,2\n"
)
CALENDAR_TXT = (
    "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date\n"
    "WD,1,1,1,1,1,0,0,20260101,20261231\n"
)


def _write_test_gtfs_zip(zip_path) -> None:
    with zipfile.ZipFile(zip_path, "w") as zip_file:
        zip_file.writestr("agency.txt", AGENCY_TXT)
        zip_file.writestr("routes.txt", ROUTES_TXT)
        zip_file.writestr("stops.txt", STOPS_TXT)
        zip_file.writestr("trips.txt", TRIPS_TXT)
        zip_file.writestr("stop_times.txt", STOP_TIMES_TXT)
        zip_file.writestr("calendar.txt", CALENDAR_TXT)
        zip_file.writestr("shapes.txt", SHAPES_TXT)


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "test.db")


@pytest.fixture
def gtfs_zip_env(tmp_path, monkeypatch):
    cta_zip = tmp_path / "cta.zip"
    dart_zip = tmp_path / "dart.zip"
    _write_test_gtfs_zip(cta_zip)
    _write_test_gtfs_zip(dart_zip)
    monkeypatch.setenv("GTFS_CTA_ZIP_PATH", str(cta_zip))
    monkeypatch.setenv("GTFS_DART_ZIP_PATH", str(dart_zip))


def test_bootstrap_fresh_database_imports_gtfs_and_seeds_scenarios(temp_db, gtfs_zip_env):
    bootstrap_production.main()

    assert gtfs_repository.count_rows("gtfs_routes", "CTA") == 1
    assert gtfs_repository.count_rows("gtfs_routes", "DART") == 1
    assert len(route_repository.list_routes()) == 12  # backend/seed_data/sample-routes.json


def test_bootstrap_is_idempotent_does_not_duplicate_rows(temp_db, gtfs_zip_env):
    bootstrap_production.main()
    bootstrap_production.main()

    assert gtfs_repository.count_rows("gtfs_routes", "CTA") == 1
    assert gtfs_repository.count_rows("gtfs_stop_times", "CTA") == 2
    assert len(route_repository.list_routes()) == 12


def test_bootstrap_skips_agency_already_imported_even_without_zip_path(temp_db, gtfs_zip_env, monkeypatch):
    bootstrap_production.main()

    # Both agencies already have data -- re-running with no zip paths at all
    # must still succeed, proving it skips rather than re-downloading/re-importing.
    monkeypatch.delenv("GTFS_CTA_ZIP_PATH", raising=False)
    monkeypatch.delenv("GTFS_DART_ZIP_PATH", raising=False)

    bootstrap_production.main()

    assert gtfs_repository.count_rows("gtfs_routes", "CTA") == 1


def test_bootstrap_fails_clearly_when_zip_path_env_var_unset(temp_db, monkeypatch):
    monkeypatch.delenv("GTFS_CTA_ZIP_PATH", raising=False)
    monkeypatch.delenv("GTFS_DART_ZIP_PATH", raising=False)

    with pytest.raises(SystemExit, match="GTFS_CTA_ZIP_PATH"):
        bootstrap_production.main()

    assert len(route_repository.list_routes()) == 0  # never got to seeding -- no half-bootstrapped DB


def test_bootstrap_fails_clearly_when_zip_file_does_not_exist(temp_db, monkeypatch, tmp_path):
    monkeypatch.setenv("GTFS_CTA_ZIP_PATH", str(tmp_path / "missing.zip"))
    monkeypatch.setenv("GTFS_DART_ZIP_PATH", str(tmp_path / "also-missing.zip"))

    with pytest.raises(SystemExit, match="does not exist"):
        bootstrap_production.main()


def test_bootstrap_leaves_database_ready_for_ensure_database_ready(temp_db, gtfs_zip_env):
    bootstrap_production.main()

    database.ensure_database_ready()  # should not raise


def test_bootstrap_resumes_after_gtfs_done_but_scenarios_unseeded(temp_db, monkeypatch, tmp_path):
    """
    Reproduces the real production failure: GTFS for both agencies already
    fully imported, but seeding crashed before curated scenarios landed.
    Re-running must finish the seeding without touching GTFS at all -- no
    zip path env vars are set here, so any attempt to re-import would fail.
    """
    from scripts.import_gtfs import import_gtfs

    cta_zip = tmp_path / "cta.zip"
    dart_zip = tmp_path / "dart.zip"
    _write_test_gtfs_zip(cta_zip)
    _write_test_gtfs_zip(dart_zip)
    import_gtfs("CTA", cta_zip)
    import_gtfs("DART", dart_zip)
    monkeypatch.delenv("GTFS_CTA_ZIP_PATH", raising=False)
    monkeypatch.delenv("GTFS_DART_ZIP_PATH", raising=False)

    assert len(route_repository.list_routes()) == 0  # confirms the partial state before the fix runs

    bootstrap_production.main()

    assert gtfs_repository.count_rows("gtfs_routes", "CTA") == 1
    assert gtfs_repository.count_rows("gtfs_stop_times", "CTA") == 2
    assert gtfs_repository.count_rows("gtfs_routes", "DART") == 1
    assert len(route_repository.list_routes()) == 12
