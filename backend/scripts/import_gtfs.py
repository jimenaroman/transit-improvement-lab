"""
Imports static GTFS files from a local ZIP into the gtfs_* SQLite tables.

Usage (from the backend/ directory):

    python scripts/import_gtfs.py --agency CTA --zip-path ../data/gtfs/cta/google_transit.zip
    python scripts/import_gtfs.py --agency DART --zip-path ../data/gtfs/dart/google_transit.zip

Safe to re-run: existing rows for the given --agency are deleted before the
new ones are inserted, so running this again (e.g. after re-downloading a
feed) just replaces that agency's data instead of duplicating it.

This is a first "spike": no downloading from the internet here (the zip must
already exist locally), no GTFS-Realtime, and only the standard library —
zipfile, csv, argparse, and sqlite3 via the repository layer. See
docs/gtfs-integration-plan.md for what comes after this.
"""

import argparse
import csv
import io
import sys
import zipfile
from pathlib import Path
from typing import Iterable

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import init_db  # noqa: E402
from app.repositories import gtfs_repository  # noqa: E402

# The GTFS files this spike knows how to import, in the order we process
# them. A real feed usually has other files too (shapes.txt, fares, etc.) —
# anything not in this list is simply ignored.
GTFS_FILENAMES = [
    "agency.txt",
    "routes.txt",
    "stops.txt",
    "trips.txt",
    "stop_times.txt",
    "calendar.txt",
    "calendar_dates.txt",
]


def _read_csv_rows(zip_file: zipfile.ZipFile, filename: str) -> Iterable[dict]:
    """Yields one dict per CSV row, keyed by GTFS column name.

    encoding="utf-8-sig" strips a leading byte-order-mark if the agency's
    feed has one — common in files exported from Windows tools — so it
    doesn't end up glued onto the first column name.
    """
    with zip_file.open(filename) as raw_file:
        text_file = io.TextIOWrapper(raw_file, encoding="utf-8-sig")
        yield from csv.DictReader(text_file)


def _to_int(value: str | None) -> int | None:
    """GTFS fields are always strings; blank/missing optional fields become None."""
    return int(value) if value not in (None, "") else None


def _to_float(value: str | None) -> float | None:
    return float(value) if value not in (None, "") else None


def _import_agency(zip_file: zipfile.ZipFile, filename: str, agency_source: str) -> int:
    rows = (
        (
            agency_source,
            row.get("agency_id"),
            row.get("agency_name"),
            row.get("agency_url"),
            row.get("agency_timezone"),
        )
        for row in _read_csv_rows(zip_file, filename)
    )
    return gtfs_repository.insert_agencies(rows)


def _import_routes(zip_file: zipfile.ZipFile, filename: str, agency_source: str) -> int:
    rows = (
        (
            agency_source,
            row.get("route_id"),
            row.get("agency_id"),
            row.get("route_short_name"),
            row.get("route_long_name"),
            row.get("route_type"),
        )
        for row in _read_csv_rows(zip_file, filename)
    )
    return gtfs_repository.insert_routes(rows)


def _import_stops(zip_file: zipfile.ZipFile, filename: str, agency_source: str) -> int:
    rows = (
        (
            agency_source,
            row.get("stop_id"),
            row.get("stop_name"),
            _to_float(row.get("stop_lat")),
            _to_float(row.get("stop_lon")),
        )
        for row in _read_csv_rows(zip_file, filename)
    )
    return gtfs_repository.insert_stops(rows)


def _import_trips(zip_file: zipfile.ZipFile, filename: str, agency_source: str) -> int:
    # Not every agency's trips.txt has trip_headsign (CTA's doesn't) —
    # row.get() returns None instead of raising KeyError for those.
    rows = (
        (
            agency_source,
            row.get("trip_id"),
            row.get("route_id"),
            row.get("service_id"),
            row.get("trip_headsign"),
            row.get("direction_id"),
        )
        for row in _read_csv_rows(zip_file, filename)
    )
    return gtfs_repository.insert_trips(rows)


def _import_stop_times(zip_file: zipfile.ZipFile, filename: str, agency_source: str) -> int:
    rows = (
        (
            agency_source,
            row.get("trip_id"),
            row.get("stop_id"),
            row.get("arrival_time"),
            row.get("departure_time"),
            _to_int(row.get("stop_sequence")),
        )
        for row in _read_csv_rows(zip_file, filename)
    )
    return gtfs_repository.insert_stop_times(rows)


def _import_calendar(zip_file: zipfile.ZipFile, filename: str, agency_source: str) -> int:
    rows = (
        (
            agency_source,
            row.get("service_id"),
            _to_int(row.get("monday")),
            _to_int(row.get("tuesday")),
            _to_int(row.get("wednesday")),
            _to_int(row.get("thursday")),
            _to_int(row.get("friday")),
            _to_int(row.get("saturday")),
            _to_int(row.get("sunday")),
            row.get("start_date"),
            row.get("end_date"),
        )
        for row in _read_csv_rows(zip_file, filename)
    )
    return gtfs_repository.insert_calendar(rows)


def _import_calendar_dates(zip_file: zipfile.ZipFile, filename: str, agency_source: str) -> int:
    rows = (
        (
            agency_source,
            row.get("service_id"),
            row.get("date"),
            row.get("exception_type"),
        )
        for row in _read_csv_rows(zip_file, filename)
    )
    return gtfs_repository.insert_calendar_dates(rows)


# Maps each known GTFS filename to the function that imports it.
_IMPORTERS = {
    "agency.txt": _import_agency,
    "routes.txt": _import_routes,
    "stops.txt": _import_stops,
    "trips.txt": _import_trips,
    "stop_times.txt": _import_stop_times,
    "calendar.txt": _import_calendar,
    "calendar_dates.txt": _import_calendar_dates,
}


def import_gtfs(agency_source: str, zip_path: Path) -> dict[str, int]:
    """
    Imports one agency's static GTFS zip.

    Returns a dict of {filename: rows_imported} for whichever of the known
    GTFS_FILENAMES were actually found in the zip. Files that are missing
    are skipped with a printed warning, not an error — GTFS technically
    allows some files to be optional, and this first spike is deliberately
    lenient about it.
    """
    init_db()
    gtfs_repository.delete_agency_data(agency_source)

    counts: dict[str, int] = {}

    with zipfile.ZipFile(zip_path) as zip_file:
        available_files = set(zip_file.namelist())

        for filename in GTFS_FILENAMES:
            if filename not in available_files:
                print(f"Warning: {filename} not found in {zip_path.name}, skipping.")
                continue

            import_one_file = _IMPORTERS[filename]
            row_count = import_one_file(zip_file, filename, agency_source)
            counts[filename] = row_count
            print(f"Imported {row_count} rows from {filename}")

    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Import a static GTFS zip into SQLite.")
    parser.add_argument("--agency", required=True, help='Agency source label, e.g. "CTA" or "DART"')
    parser.add_argument("--zip-path", required=True, type=Path, help="Path to the GTFS zip file")
    args = parser.parse_args()

    import_gtfs(args.agency.upper(), args.zip_path)


if __name__ == "__main__":
    main()
