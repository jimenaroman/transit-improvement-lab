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
from typing import Iterator

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


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
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
    """Creates the trip_scenarios table if it doesn't already exist."""
    with get_connection() as connection:
        connection.execute(CREATE_TRIP_SCENARIOS_TABLE)
