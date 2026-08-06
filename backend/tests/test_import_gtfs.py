"""
Tests for scripts/import_gtfs.py.

These build a tiny hand-written GTFS zip on disk (six files, a handful of
rows each) rather than using the real CTA/DART zips, so tests stay fast and
don't depend on multi-gigabyte fixtures. calendar_dates.txt is deliberately
left out of the test zip to exercise the "missing optional file" warning.
"""

import zipfile

import pytest

from app import database
from app.repositories import gtfs_repository
from scripts.import_gtfs import import_gtfs

AGENCY_TXT = "agency_id,agency_name,agency_url,agency_timezone\n1,Test Transit,http://example.com,America/Chicago\n"

ROUTES_TXT = "route_id,agency_id,route_short_name,route_long_name,route_type\nR1,1,1,Test Route One,3\n"

STOPS_TXT = (
    "stop_id,stop_name,stop_lat,stop_lon\n"
    "S1,First Stop,41.8,-87.6\n"
    "S2,Second Stop,41.9,-87.7\n"
)

# Deliberately omits trip_headsign, matching CTA's real trips.txt, to check
# that a missing optional column doesn't crash the import.
TRIPS_TXT = "route_id,service_id,trip_id,direction_id\nR1,WD,T1,0\n"

STOP_TIMES_TXT = (
    "trip_id,arrival_time,departure_time,stop_id,stop_sequence\n"
    "T1,08:00:00,08:00:00,S1,1\n"
    "T1,08:05:00,08:05:00,S2,2\n"
)

CALENDAR_TXT = (
    "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date\n"
    "WD,1,1,1,1,1,0,0,20260101,20261231\n"
)


def _write_test_gtfs_zip(zip_path, include_calendar_dates: bool = False) -> None:
    with zipfile.ZipFile(zip_path, "w") as zip_file:
        zip_file.writestr("agency.txt", AGENCY_TXT)
        zip_file.writestr("routes.txt", ROUTES_TXT)
        zip_file.writestr("stops.txt", STOPS_TXT)
        zip_file.writestr("trips.txt", TRIPS_TXT)
        zip_file.writestr("stop_times.txt", STOP_TIMES_TXT)
        zip_file.writestr("calendar.txt", CALENDAR_TXT)
        if include_calendar_dates:
            zip_file.writestr("calendar_dates.txt", "service_id,date,exception_type\nWD,20260704,2\n")


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "test.db")


def test_import_gtfs_counts_and_stores_rows(temp_db, tmp_path):
    zip_path = tmp_path / "test_feed.zip"
    _write_test_gtfs_zip(zip_path)

    counts = import_gtfs("CTA", zip_path)

    assert counts == {
        "agency.txt": 1,
        "routes.txt": 1,
        "stops.txt": 2,
        "trips.txt": 1,
        "stop_times.txt": 2,
        "calendar.txt": 1,
    }
    assert "calendar_dates.txt" not in counts

    assert gtfs_repository.count_rows("gtfs_agencies", "CTA") == 1
    assert gtfs_repository.count_rows("gtfs_routes", "CTA") == 1
    assert gtfs_repository.count_rows("gtfs_stops", "CTA") == 2
    assert gtfs_repository.count_rows("gtfs_trips", "CTA") == 1
    assert gtfs_repository.count_rows("gtfs_stop_times", "CTA") == 2
    assert gtfs_repository.count_rows("gtfs_calendar", "CTA") == 1
    assert gtfs_repository.count_rows("gtfs_calendar_dates", "CTA") == 0


def test_missing_optional_file_prints_a_warning(temp_db, tmp_path, capsys):
    zip_path = tmp_path / "test_feed.zip"
    _write_test_gtfs_zip(zip_path)  # calendar_dates.txt intentionally absent

    import_gtfs("CTA", zip_path)

    output = capsys.readouterr().out
    assert "calendar_dates.txt" in output
    assert "not found" in output


def test_import_is_safely_rerunnable(temp_db, tmp_path):
    zip_path = tmp_path / "test_feed.zip"
    _write_test_gtfs_zip(zip_path)

    import_gtfs("CTA", zip_path)
    import_gtfs("CTA", zip_path)  # re-running should replace, not duplicate

    assert gtfs_repository.count_rows("gtfs_stops", "CTA") == 2
    assert gtfs_repository.count_rows("gtfs_stop_times", "CTA") == 2


def test_import_keeps_agencies_separate(temp_db, tmp_path):
    cta_zip = tmp_path / "cta_feed.zip"
    dart_zip = tmp_path / "dart_feed.zip"
    _write_test_gtfs_zip(cta_zip)
    _write_test_gtfs_zip(dart_zip, include_calendar_dates=True)

    import_gtfs("CTA", cta_zip)
    import_gtfs("DART", dart_zip)

    assert gtfs_repository.count_rows("gtfs_stops", "CTA") == 2
    assert gtfs_repository.count_rows("gtfs_stops", "DART") == 2
    assert gtfs_repository.count_rows("gtfs_calendar_dates", "CTA") == 0
    assert gtfs_repository.count_rows("gtfs_calendar_dates", "DART") == 1

    # Re-importing DART must not touch CTA's rows.
    import_gtfs("DART", dart_zip)
    assert gtfs_repository.count_rows("gtfs_stops", "CTA") == 2


def test_missing_trip_headsign_column_does_not_crash(temp_db, tmp_path):
    # TRIPS_TXT above already omits trip_headsign, matching CTA's real feed.
    zip_path = tmp_path / "test_feed.zip"
    _write_test_gtfs_zip(zip_path)

    import_gtfs("CTA", zip_path)

    assert gtfs_repository.count_rows("gtfs_trips", "CTA") == 1
