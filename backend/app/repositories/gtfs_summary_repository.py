"""
Repository for read-only GTFS summary queries (/api/gtfs/...).

This is separate from gtfs_repository.py on purpose: gtfs_repository.py
holds the import-time write functions (insert_*, delete_agency_data) used
by scripts/import_gtfs.py, while this file holds the read-only aggregate
queries the API actually serves — the same split already used between
route_repository.py (route reads) and dashboard_repository.py (aggregate
summary reads over the same trip_scenarios table).

Agency matching is case-insensitive throughout (LOWER(...) = LOWER(?)),
the same pattern route_repository.list_routes() already uses for its city
filter, since agency_source is stored uppercase ("CTA", "DART") but a
caller might reasonably request "cta" in a URL.
"""

from app.database import get_connection
from app.gtfs_schemas import AgencyGtfsCounts, GtfsRouteWithTripCount

# Tables counted per agency for the /summary endpoint. gtfs_agencies isn't
# included — its count per agency is always 1, so it isn't a useful summary
# figure the way "how many stops does this agency have" is.
GTFS_COUNT_TABLES = {
    "routes": "gtfs_routes",
    "stops": "gtfs_stops",
    "trips": "gtfs_trips",
    "stop_times": "gtfs_stop_times",
    "calendar": "gtfs_calendar",
    "calendar_dates": "gtfs_calendar_dates",
}

ROUTES_WITH_TRIP_COUNTS_SELECT = """
    SELECT
      r.route_id,
      r.route_short_name,
      r.route_long_name,
      r.route_type,
      COUNT(t.id) AS trip_count
    FROM gtfs_routes r
    LEFT JOIN gtfs_trips t
      ON t.route_id = r.route_id AND t.agency_source = r.agency_source
    WHERE LOWER(r.agency_source) = LOWER(?)
    GROUP BY r.route_id, r.route_short_name, r.route_long_name, r.route_type
"""


def _count_by_agency(table: str) -> dict[str, int]:
    """Returns {agency_source: row_count} for one gtfs_* table."""
    with get_connection() as connection:
        rows = connection.execute(
            f"SELECT agency_source, COUNT(*) AS total FROM {table} GROUP BY agency_source"
        ).fetchall()

    return {row["agency_source"]: row["total"] for row in rows}


def get_summary() -> list[AgencyGtfsCounts]:
    counts_by_metric = {metric: _count_by_agency(table) for metric, table in GTFS_COUNT_TABLES.items()}

    # Union the agencies seen across every table, so an agency that's only
    # partially imported (e.g. routes loaded but stop_times still pending)
    # shows up with 0s instead of being silently left out entirely.
    all_agencies: set[str] = set()
    for counts in counts_by_metric.values():
        all_agencies.update(counts.keys())

    return [
        AgencyGtfsCounts(
            agency_source=agency,
            routes=counts_by_metric["routes"].get(agency, 0),
            stops=counts_by_metric["stops"].get(agency, 0),
            trips=counts_by_metric["trips"].get(agency, 0),
            stop_times=counts_by_metric["stop_times"].get(agency, 0),
            calendar=counts_by_metric["calendar"].get(agency, 0),
            calendar_dates=counts_by_metric["calendar_dates"].get(agency, 0),
        )
        for agency in sorted(all_agencies)
    ]


def get_routes_for_agency(agency_source: str) -> list[GtfsRouteWithTripCount]:
    with get_connection() as connection:
        rows = connection.execute(
            ROUTES_WITH_TRIP_COUNTS_SELECT + " ORDER BY r.route_id",
            (agency_source,),
        ).fetchall()

    return [GtfsRouteWithTripCount(**dict(row)) for row in rows]


def get_top_routes_by_trips(agency_source: str, limit: int = 10) -> list[GtfsRouteWithTripCount]:
    with get_connection() as connection:
        rows = connection.execute(
            ROUTES_WITH_TRIP_COUNTS_SELECT + " ORDER BY trip_count DESC, r.route_id LIMIT ?",
            (agency_source, limit),
        ).fetchall()

    return [GtfsRouteWithTripCount(**dict(row)) for row in rows]
