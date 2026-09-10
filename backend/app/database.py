"""
V1 SQLite connection layer.

This is the initial database layer for Transit Improvement Lab. It replaces
the temporary sample-routes.json file with a real SQLite database, so
route scenarios live in the database instead of being re-read from disk as
JSON on every request. The repository layer (app/repositories/) is the only
code that should import from this module — everything else should go
through the repository functions.
"""

import sqlite3
from contextlib import contextmanager
from typing import Generator

from app.config import get_database_path

DB_PATH = get_database_path()

CREATE_TRIP_SCENARIOS_TABLE = """
CREATE TABLE IF NOT EXISTS trip_scenarios (
  id INTEGER PRIMARY KEY,
  city TEXT NOT NULL,
  origin_label TEXT NOT NULL,
  destination_label TEXT NOT NULL,
  route_category TEXT NOT NULL,
  time_period TEXT NOT NULL,
  distance_miles REAL NOT NULL,
  driving_minutes INTEGER NOT NULL,
  transit_minutes INTEGER NOT NULL,
  walking_minutes INTEGER NOT NULL,
  wait_transfer_minutes INTEGER NOT NULL,
  transfers INTEGER NOT NULL,
  fare_cost REAL NOT NULL,
  gas_cost REAL NOT NULL,
  driving_emissions_kg REAL NOT NULL,
  transit_emissions_kg REAL NOT NULL,
  notes TEXT NOT NULL
);
"""

# GTFS (General Transit Feed Specification) static schedule tables. Every
# table carries agency_source ("CTA", "DART", ...) so more than one agency's
# data can live side by side, and scripts/import_gtfs.py can safely clear
# and re-import just one agency at a time without touching the others.
# These columns are a subset of the real GTFS spec — enough for the first
# import spike, not the full field list every agency publishes.
CREATE_GTFS_TABLES = [
    """
    CREATE TABLE IF NOT EXISTS gtfs_agencies (
      id INTEGER PRIMARY KEY,
      agency_source TEXT NOT NULL,
      agency_id TEXT,
      agency_name TEXT,
      agency_url TEXT,
      agency_timezone TEXT
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS gtfs_routes (
      id INTEGER PRIMARY KEY,
      agency_source TEXT NOT NULL,
      route_id TEXT NOT NULL,
      agency_id TEXT,
      route_short_name TEXT,
      route_long_name TEXT,
      route_type TEXT
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS gtfs_stops (
      id INTEGER PRIMARY KEY,
      agency_source TEXT NOT NULL,
      stop_id TEXT NOT NULL,
      stop_name TEXT,
      stop_lat REAL,
      stop_lon REAL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS gtfs_trips (
      id INTEGER PRIMARY KEY,
      agency_source TEXT NOT NULL,
      trip_id TEXT NOT NULL,
      route_id TEXT,
      service_id TEXT,
      trip_headsign TEXT,
      direction_id TEXT,
      shape_id TEXT
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS gtfs_stop_times (
      id INTEGER PRIMARY KEY,
      agency_source TEXT NOT NULL,
      trip_id TEXT NOT NULL,
      stop_id TEXT NOT NULL,
      arrival_time TEXT,
      departure_time TEXT,
      stop_sequence INTEGER
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS gtfs_calendar (
      id INTEGER PRIMARY KEY,
      agency_source TEXT NOT NULL,
      service_id TEXT NOT NULL,
      monday INTEGER,
      tuesday INTEGER,
      wednesday INTEGER,
      thursday INTEGER,
      friday INTEGER,
      saturday INTEGER,
      sunday INTEGER,
      start_date TEXT,
      end_date TEXT
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS gtfs_calendar_dates (
      id INTEGER PRIMARY KEY,
      agency_source TEXT NOT NULL,
      service_id TEXT NOT NULL,
      date TEXT,
      exception_type TEXT
    );
    """,
    # Route-line geometry (shapes.txt). shape_dist_traveled is optional per
    # the GTFS spec -- not every agency's feed includes it -- so it's
    # nullable, unlike the required lat/lon/sequence columns.
    """
    CREATE TABLE IF NOT EXISTS gtfs_shapes (
      id INTEGER PRIMARY KEY,
      agency_source TEXT NOT NULL,
      shape_id TEXT NOT NULL,
      shape_pt_lat REAL NOT NULL,
      shape_pt_lon REAL NOT NULL,
      shape_pt_sequence INTEGER NOT NULL,
      shape_dist_traveled REAL
    );
    """,
]

# Indexes supporting the geometry lookup path: gtfs_trips -> candidate
# shape_ids for a route, then gtfs_shapes -> ordered points for one shape_id.
CREATE_GTFS_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_gtfs_shapes_shape_lookup "
    "ON gtfs_shapes (agency_source, shape_id, shape_pt_sequence);",
    "CREATE INDEX IF NOT EXISTS idx_gtfs_trips_route_lookup "
    "ON gtfs_trips (agency_source, route_id, shape_id);",
    # Without this, get_first_stop_departure_times() full-scans
    # gtfs_stop_times (5.8M rows for CTA) instead of seeking by trip_id.
    "CREATE INDEX IF NOT EXISTS idx_gtfs_stop_times_trip_lookup "
    "ON gtfs_stop_times (agency_source, trip_id, stop_sequence);",
]

# Manual, curated association between a trip_scenarios row (the
# product-level trip shown in route comparisons) and one or more real GTFS
# routes that provide scheduled-service evidence for it. Seeded by hand
# from backend/seed_data/scenario-gtfs-links.json -- this app does not infer these
# geographically. The UNIQUE constraint stops the same scenario/agency/
# route combination from being linked twice.
CREATE_TRIP_SCENARIO_GTFS_ROUTES_TABLE = """
CREATE TABLE IF NOT EXISTS trip_scenario_gtfs_routes (
  id INTEGER PRIMARY KEY,
  scenario_id INTEGER NOT NULL,
  agency_source TEXT NOT NULL,
  route_id TEXT NOT NULL,
  role TEXT,
  UNIQUE(scenario_id, agency_source, route_id)
);
"""


@contextmanager
def get_connection() -> Generator[sqlite3.Connection, None, None]:
    """
    Opens a connection, yields it, then commits and closes it.

    Reading DB_PATH here (rather than baking it into a default argument)
    means tests can point this module at a temporary database file.
    """
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def _add_column_if_missing(connection: sqlite3.Connection, table: str, column: str, column_type: str) -> None:
    """
    Adds `column` to `table` if it isn't already there.

    CREATE TABLE IF NOT EXISTS only helps on a brand-new database file --
    an existing gtfs_trips table (like the one already checked into a
    developer's local transit_lab.db) keeps whatever columns it had when it
    was first created. This lets gtfs_trips.shape_id show up on both a
    fresh database and one that predates it, without anyone needing to
    delete their local .db file by hand.
    """
    existing_columns = {row["name"] for row in connection.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in existing_columns:
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")


def init_db() -> None:
    """Creates the trip_scenarios, gtfs_*, and association tables if they don't already exist."""
    with get_connection() as connection:
        connection.execute(CREATE_TRIP_SCENARIOS_TABLE)
        for create_table_statement in CREATE_GTFS_TABLES:
            connection.execute(create_table_statement)
        connection.execute(CREATE_TRIP_SCENARIO_GTFS_ROUTES_TABLE)
        _add_column_if_missing(connection, "gtfs_trips", "shape_id", "TEXT")
        for create_index_statement in CREATE_GTFS_INDEXES:
            connection.execute(create_index_statement)


def ensure_database_ready() -> None:
    """
    Raises RuntimeError if the configured database doesn't exist or has no
    curated scenarios yet, instead of silently serving an empty database.
    Called once from FastAPI's startup lifespan, not from every import.
    """
    if not DB_PATH.exists():
        raise RuntimeError(
            f"Database not found at {DB_PATH}. Run the production bootstrap first: "
            "python -m app.bootstrap_production"
        )

    with get_connection() as connection:
        try:
            row = connection.execute("SELECT COUNT(*) AS total FROM trip_scenarios").fetchone()
        except sqlite3.OperationalError as error:
            raise RuntimeError(
                f"Database at {DB_PATH} is not initialized ({error}). Run: python -m app.bootstrap_production"
            ) from error

    if row["total"] == 0:
        raise RuntimeError(
            f"Database at {DB_PATH} has no curated scenarios yet. Run: python -m app.bootstrap_production"
        )
