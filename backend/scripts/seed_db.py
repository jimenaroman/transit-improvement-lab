"""
Seeds transit_lab.db from data/sample-routes.json.

Run from the backend/ directory:

    python scripts/seed_db.py

Safe to re-run: it recreates the table if needed and replaces all rows,
so running it again after editing sample-routes.json just re-syncs the
database with the JSON file.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import init_db  # noqa: E402
from app.repositories.route_repository import replace_all_routes  # noqa: E402
from app.services.data_loader import load_routes  # noqa: E402


def seed() -> None:
    routes = load_routes()
    init_db()
    replace_all_routes(routes)
    print(f"Seeded {len(routes)} route scenarios into transit_lab.db")


if __name__ == "__main__":
    seed()
