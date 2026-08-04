"""
Repository layer for the trip_scenarios table.

This module is the only place that writes raw SQL. Everything else (API
routes, the seed script, tests) calls these functions and works with
RouteScenario objects, never with sqlite3.Row or SQL strings directly.
"""

import sqlite3

from app.database import get_connection
from app.schemas import RouteScenario

INSERT_TRIP_SCENARIO = """
INSERT INTO trip_scenarios (
    id, city, origin_label, destination_label, route_category,
    time_period, distance_miles, driving_minutes, transit_minutes,
    walking_minutes, wait_transfer_minutes, transfers, fare_cost,
    gas_cost, driving_emissions_kg, transit_emissions_kg, notes
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""


def _route_to_params(route: RouteScenario) -> tuple:
    return (
        route.id,
        route.city,
        route.origin_label,
        route.destination_label,
        route.route_category,
        route.time_period,
        route.distance_miles,
        route.driving_minutes,
        route.transit_minutes,
        route.walking_minutes,
        route.wait_transfer_minutes,
        route.transfers,
        route.fare_cost,
        route.gas_cost,
        route.driving_emissions_kg,
        route.transit_emissions_kg,
        route.notes,
    )


def _row_to_route(row: sqlite3.Row) -> RouteScenario:
    return RouteScenario(**dict(row))


def list_routes(city: str | None = None) -> list[RouteScenario]:
    query = "SELECT * FROM trip_scenarios ORDER BY id"
    params: tuple = ()

    if city:
        query = "SELECT * FROM trip_scenarios WHERE LOWER(city) = LOWER(?) ORDER BY id"
        params = (city,)

    with get_connection() as connection:
        rows = connection.execute(query, params).fetchall()

    return [_row_to_route(row) for row in rows]


def get_route_by_id(route_id: int) -> RouteScenario | None:
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM trip_scenarios WHERE id = ?", (route_id,)
        ).fetchone()

    return _row_to_route(row) if row else None


def replace_all_routes(routes: list[RouteScenario]) -> None:
    """Clears the table and inserts the given routes. Used by the seed script."""
    with get_connection() as connection:
        connection.execute("DELETE FROM trip_scenarios")
        connection.executemany(INSERT_TRIP_SCENARIO, [_route_to_params(route) for route in routes])
