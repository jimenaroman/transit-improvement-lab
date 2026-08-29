"""
Repository for real GTFS route-line geometry (shapes.txt), used by the
Analyze Trip map.

A route can have more than one shape_id -- inbound vs. outbound, branches,
short-turns -- and GTFS gives no single "the" shape for a route. This app
never guesses or interpolates geometry, so for V1 it picks one shape
deterministically: the shape_id used by the most trips on that route,
tying broken alphabetically by shape_id so the choice is stable across
re-imports. That's a documented limitation, not a claim that the chosen
shape is the "correct" or only real alignment -- see the shapes.txt
section of docs/gtfs-integration-plan.md.
"""

from app.database import get_connection


def find_representative_shape_id(agency_source: str, route_id: str) -> str | None:
    """
    Returns the shape_id used by the most trips on this route, or None if
    the route has no trips with a shape_id at all.

    Empty-string shape_ids are excluded along with NULLs -- some feeds use
    "" rather than an absent column to mean "no shape for this trip."
    """
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT shape_id, COUNT(*) AS trip_count
            FROM gtfs_trips
            WHERE LOWER(agency_source) = LOWER(?)
              AND route_id = ?
              AND shape_id IS NOT NULL
              AND shape_id != ''
            GROUP BY shape_id
            ORDER BY trip_count DESC, shape_id ASC
            LIMIT 1
            """,
            (agency_source, route_id),
        ).fetchone()

    return row["shape_id"] if row is not None else None


def get_shape_points(agency_source: str, shape_id: str) -> list[dict]:
    """Returns one shape's points in GTFS shape_pt_sequence order."""
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT shape_pt_lat, shape_pt_lon, shape_pt_sequence, shape_dist_traveled
            FROM gtfs_shapes
            WHERE LOWER(agency_source) = LOWER(?) AND shape_id = ?
            ORDER BY shape_pt_sequence ASC
            """,
            (agency_source, shape_id),
        ).fetchall()

    return [dict(row) for row in rows]
