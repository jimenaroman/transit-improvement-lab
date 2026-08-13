"""
Repository for the trip_scenario_gtfs_routes association table -- the
manual, curated link between a trip_scenarios row (the product-level trip
shown in route comparisons) and one or more real GTFS routes that provide
scheduled-service evidence for it.

Like every repository in this codebase, this file only runs SQL and
returns plain values. The associations themselves are seeded by hand from
data/scenario-gtfs-links.json via scripts/seed_scenario_gtfs_links.py --
this app does not infer them geographically.
"""

from app.database import get_connection


def scenario_exists(scenario_id: int) -> bool:
    with get_connection() as connection:
        row = connection.execute("SELECT 1 FROM trip_scenarios WHERE id = ? LIMIT 1", (scenario_id,)).fetchone()

    return row is not None


def route_exists(agency_source: str, route_id: str) -> bool:
    """Optional validation: confirms a GTFS route actually exists before linking a scenario to it."""
    with get_connection() as connection:
        row = connection.execute(
            "SELECT 1 FROM gtfs_routes WHERE LOWER(agency_source) = LOWER(?) AND route_id = ? LIMIT 1",
            (agency_source, route_id),
        ).fetchone()

    return row is not None


def list_links_for_scenario(scenario_id: int) -> list[dict]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT agency_source, route_id, role
            FROM trip_scenario_gtfs_routes
            WHERE scenario_id = ?
            ORDER BY id
            """,
            (scenario_id,),
        ).fetchall()

    return [dict(row) for row in rows]


def replace_links_for_scenario(scenario_id: int, links: list[dict]) -> None:
    """
    Replaces all of one scenario's GTFS route links with the given list.

    Each link dict needs "agency_source" and "route_id"; "role" is
    optional. Always deletes existing links for this scenario first, so
    calling this repeatedly re-syncs rather than duplicates -- the
    trip_scenario_gtfs_routes UNIQUE constraint would otherwise reject a
    second identical link anyway.
    """
    with get_connection() as connection:
        connection.execute("DELETE FROM trip_scenario_gtfs_routes WHERE scenario_id = ?", (scenario_id,))
        connection.executemany(
            """
            INSERT INTO trip_scenario_gtfs_routes (scenario_id, agency_source, route_id, role)
            VALUES (?, ?, ?, ?)
            """,
            [(scenario_id, link["agency_source"], link["route_id"], link.get("role")) for link in links],
        )
