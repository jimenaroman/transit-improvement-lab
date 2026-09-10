"""
Seed data loader.

Route scenarios now live in SQLite (see app/database.py and
app/repositories/route_repository.py) — the API no longer reads this file
directly. This module's only remaining job is parsing and validating
backend/seed_data/sample-routes.json for scripts/seed_db.py, which loads it
into the database.
"""

import json
from pathlib import Path

from app.schemas import RouteScenario

# parents[2] from here is backend/ itself, so this stays correct whether
# backend/ is checked out inside the monorepo or deployed on its own.
DATA_PATH = Path(__file__).resolve().parents[2] / "seed_data" / "sample-routes.json"


def load_routes() -> list[RouteScenario]:
    with open(DATA_PATH, "r", encoding="utf-8") as file:
        raw_routes = json.load(file)

    return [RouteScenario(**route) for route in raw_routes]
