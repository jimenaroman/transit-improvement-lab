"""
Temporary V0 data access layer.

For the first backend milestone, route scenarios are loaded from
data/sample-routes.json so the API can work before a database is added.

Later, this module should be replaced or refactored into a repository layer
that reads route scenarios from SQLite/PostgreSQL.
"""

import json
from pathlib import Path

from app.schemas import RouteScenario


DATA_PATH = Path(__file__).resolve().parents[3] / "data" / "sample-routes.json"


def load_routes() -> list[RouteScenario]:
    with open(DATA_PATH, "r", encoding="utf-8") as file:
        raw_routes = json.load(file)

    return [RouteScenario(**route) for route in raw_routes]


def get_route_by_id(route_id: int) -> RouteScenario | None:
    routes = load_routes()

    for route in routes:
        if route.id == route_id:
            return route

    return None
