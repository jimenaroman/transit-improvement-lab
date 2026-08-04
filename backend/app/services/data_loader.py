"""
Seed data loader.

Route scenarios now live in SQLite (see app/database.py and
app/repositories/route_repository.py) — the API no longer reads this file
directly. This module's only remaining job is parsing and validating
data/sample-routes.json for scripts/seed_db.py, which loads it into the
database.
"""

import json
from pathlib import Path

from app.schemas import RouteScenario


DATA_PATH = Path(__file__).resolve().parents[3] / "data" / "sample-routes.json"


def load_routes() -> list[RouteScenario]:
    with open(DATA_PATH, "r", encoding="utf-8") as file:
        raw_routes = json.load(file)

    return [RouteScenario(**route) for route in raw_routes]
