"""
Repository for GTFS static schedule data (agencies, routes, stops, trips,
stop times, and calendar tables).

Like route_repository.py, this is the only place that writes SQL for these
tables. scripts/import_gtfs.py calls these functions instead of running SQL
itself, and tests call them directly against a temporary database.

Every gtfs_* table has an agency_source column ("CTA", "DART", ...), so more
than one agency's data can live in the same tables at once. Rows are
inserted in batches (BATCH_SIZE at a time) instead of one at a time, because
a real agency's stop_times.txt can have millions of rows — CTA's has over
5.8 million — and inserting those one statement at a time would be far too
slow.

Table names below are always one of the fixed constants in GTFS_TABLES,
never a caller-supplied value, so building SQL strings with f-strings here
is safe — there's no user input involved.
"""

from typing import Iterable

from app.database import get_connection

BATCH_SIZE = 2000

GTFS_TABLES = [
    "gtfs_agencies",
    "gtfs_routes",
    "gtfs_stops",
    "gtfs_trips",
    "gtfs_stop_times",
    "gtfs_calendar",
    "gtfs_calendar_dates",
]


def _insert_in_batches(table: str, columns: list[str], rows: Iterable[tuple]) -> int:
    """Inserts rows into `table` in chunks of BATCH_SIZE. Returns how many rows were inserted."""
    column_list = ", ".join(columns)
    placeholders = ", ".join("?" for _ in columns)
    insert_sql = f"INSERT INTO {table} ({column_list}) VALUES ({placeholders})"

    total = 0
    batch: list[tuple] = []

    with get_connection() as connection:
        for row in rows:
            batch.append(row)
            if len(batch) >= BATCH_SIZE:
                connection.executemany(insert_sql, batch)
                total += len(batch)
                batch.clear()

        if batch:
            connection.executemany(insert_sql, batch)
            total += len(batch)

    return total


def delete_agency_data(agency_source: str) -> None:
    """Deletes every GTFS row for one agency, so importing is safely re-runnable."""
    with get_connection() as connection:
        for table in GTFS_TABLES:
            connection.execute(f"DELETE FROM {table} WHERE agency_source = ?", (agency_source,))


def insert_agencies(rows: Iterable[tuple]) -> int:
    return _insert_in_batches(
        "gtfs_agencies",
        ["agency_source", "agency_id", "agency_name", "agency_url", "agency_timezone"],
        rows,
    )


def insert_routes(rows: Iterable[tuple]) -> int:
    return _insert_in_batches(
        "gtfs_routes",
        ["agency_source", "route_id", "agency_id", "route_short_name", "route_long_name", "route_type"],
        rows,
    )


def insert_stops(rows: Iterable[tuple]) -> int:
    return _insert_in_batches(
        "gtfs_stops",
        ["agency_source", "stop_id", "stop_name", "stop_lat", "stop_lon"],
        rows,
    )


def insert_trips(rows: Iterable[tuple]) -> int:
    return _insert_in_batches(
        "gtfs_trips",
        ["agency_source", "trip_id", "route_id", "service_id", "trip_headsign", "direction_id"],
        rows,
    )


def insert_stop_times(rows: Iterable[tuple]) -> int:
    return _insert_in_batches(
        "gtfs_stop_times",
        ["agency_source", "trip_id", "stop_id", "arrival_time", "departure_time", "stop_sequence"],
        rows,
    )


def insert_calendar(rows: Iterable[tuple]) -> int:
    return _insert_in_batches(
        "gtfs_calendar",
        [
            "agency_source",
            "service_id",
            "monday",
            "tuesday",
            "wednesday",
            "thursday",
            "friday",
            "saturday",
            "sunday",
            "start_date",
            "end_date",
        ],
        rows,
    )


def insert_calendar_dates(rows: Iterable[tuple]) -> int:
    return _insert_in_batches(
        "gtfs_calendar_dates",
        ["agency_source", "service_id", "date", "exception_type"],
        rows,
    )


def count_rows(table: str, agency_source: str) -> int:
    """Counts rows for one agency in one gtfs_* table. Mainly used by tests."""
    with get_connection() as connection:
        row = connection.execute(
            f"SELECT COUNT(*) AS total FROM {table} WHERE agency_source = ?", (agency_source,)
        ).fetchone()

    return row["total"]
