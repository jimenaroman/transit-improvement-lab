"""
Seeds trip_scenario_gtfs_routes from data/scenario-gtfs-links.json.

Run from the backend/ directory:

    python scripts/seed_scenario_gtfs_links.py

Safe to re-run: each scenario's associations are fully replaced, not
appended, so re-running after editing the JSON file just re-syncs it.

This is a manual, curated association layer for V1. It intentionally does
not try to geographically infer which GTFS route matches a scenario --
every entry in the JSON file was individually verified against the real
imported GTFS data (by joining stops to routes) before being added. Some
scenarios have no entry at all because their origin or destination was too
vague to confidently name a single real route -- that's deliberate, not
missing data.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import init_db  # noqa: E402
from app.repositories import scenario_gtfs_link_repository  # noqa: E402

LINKS_PATH = Path(__file__).resolve().parents[2] / "data" / "scenario-gtfs-links.json"


def seed() -> None:
    with open(LINKS_PATH, "r", encoding="utf-8") as file:
        scenario_links = json.load(file)

    init_db()

    for entry in scenario_links:
        scenario_id = entry["scenario_id"]

        if not scenario_gtfs_link_repository.scenario_exists(scenario_id):
            print(f"Warning: scenario_id {scenario_id} not found in trip_scenarios, skipping.")
            continue

        valid_links = []
        for link in entry["routes"]:
            if not scenario_gtfs_link_repository.route_exists(link["agency_source"], link["route_id"]):
                print(
                    f"Warning: {link['agency_source']} route {link['route_id']} not found in gtfs_routes "
                    f"(scenario_id {scenario_id}), skipping this link."
                )
                continue
            valid_links.append(link)

        scenario_gtfs_link_repository.replace_links_for_scenario(scenario_id, valid_links)
        print(f"Linked scenario {scenario_id} to {len(valid_links)} GTFS route(s).")


if __name__ == "__main__":
    seed()
