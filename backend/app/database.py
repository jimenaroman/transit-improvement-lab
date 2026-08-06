"""
V1 SQLite connection layer.

This is the initial database layer for Transit Improvement Lab. It replaces
the temporary data/sample-routes.json file with a real SQLite database, so
route scenarios live in the database instead of being re-read from disk as
JSON on every request. The repository layer (app/repositories/) is the only
code that should import from this module — everything else should go
through the repository functions.
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

DB_PATH = Path(__file__).resolve().parents[1] / "transit_lab.db"

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
      direction_id TEXT
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
]


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


def init_db() -> None:
    """Creates the trip_scenarios and gtfs_* tables if they don't already exist."""
    with get_connection() as connection:
        connection.execute(CREATE_TRIP_SCENARIOS_TABLE)
        for create_table_statement in CREATE_GTFS_TABLES:
            connection.execute(create_table_statement)
