"""
Repository for single-route GTFS service-summary queries.

Separate from gtfs_summary_repository.py because this serves one specific
route in detail — every first-stop departure time for it, to be fed into
the headway calculations in services/gtfs_metrics.py — rather than
aggregate counts across many routes at once. As with every repository in
this codebase, this file only runs SQL and returns plain values; the
headway math itself lives in the service layer, not here.
"""

from app.database import get_connection


def get_route(agency_source: str, route_id: str) -> dict | None:
    """
    Looks up one route's metadata.

    agency_source is matched case-insensitively, same as the rest of the
    GTFS API, since it's a label this app assigns ("CTA", "DART"). route_id
    is matched exactly — it's an opaque identifier from the GTFS feed
    itself, not something to fuzzy-match.
    """
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT agency_source, route_id, route_short_name, route_long_name, route_type
            FROM gtfs_routes
            WHERE LOWER(agency_source) = LOWER(?) AND route_id = ?
            """,
            (agency_source, route_id),
        ).fetchone()

    return dict(row) if row is not None else None


def get_first_stop_departure_times(agency_source: str, route_id: str, active_service_ids: list[str]) -> list[str]:
    """
    Returns the raw GTFS departure_time string ("HH:MM:SS", possibly past
    "24:00:00") for every trip on this route whose service_id is in
    active_service_ids, taken from each trip's stop_sequence = 1 row — i.e.
    when each scheduled trip starts.

    active_service_ids scopes this to trips actually running on one
    requested date (see gtfs_metrics.compute_active_service_ids) — without
    it, every calendar pattern a route has ever had (weekday, Saturday,
    Sunday, holidays, ...) gets pooled together, which is what originally
    produced an implausible sub-minute average headway for CTA route 79.

    An empty active_service_ids list means "nothing is active" and
    correctly returns no rows — SQLite's IN () on an empty list matches
    nothing, so no special-case is needed for that.

    The join includes agency_source on both sides on purpose: trip_id is
    only guaranteed unique within one agency's feed, so CTA and DART could
    both have a trip_id "T1". Joining on trip_id alone would silently mix
    the two agencies' stop_times together.
    """
    if not active_service_ids:
        return []

    placeholders = ", ".join("?" for _ in active_service_ids)

    with get_connection() as connection:
        rows = connection.execute(
            f"""
            SELECT st.departure_time
            FROM gtfs_stop_times st
            JOIN gtfs_trips t
              ON t.trip_id = st.trip_id AND t.agency_source = st.agency_source
            WHERE LOWER(t.agency_source) = LOWER(?)
              AND t.route_id = ?
              AND st.stop_sequence = 1
              AND t.service_id IN ({placeholders})
            """,
            (agency_source, route_id, *active_service_ids),
        ).fetchall()

    return [row["departure_time"] for row in rows if row["departure_time"] is not None]


def get_agency_timezone(agency_source: str) -> str | None:
    """Looks up one agency's timezone (e.g. "America/Chicago") from gtfs_agencies."""
    with get_connection() as connection:
        row = connection.execute(
            "SELECT agency_timezone FROM gtfs_agencies WHERE LOWER(agency_source) = LOWER(?) LIMIT 1",
            (agency_source,),
        ).fetchone()

    return row["agency_timezone"] if row is not None and row["agency_timezone"] else None


def get_calendar_service_ids_for_weekday(agency_source: str, weekday_column: str, gtfs_date: str) -> list[str]:
    """
    Returns service_ids from gtfs_calendar whose date range covers
    gtfs_date and whose weekday_column is 1.

    gtfs_date must be in GTFS's own "YYYYMMDD" format (matching how
    start_date/end_date are stored), not "YYYY-MM-DD".

    weekday_column is always one of the fixed GTFS_WEEKDAY_COLUMNS names
    from services/gtfs_metrics.py, chosen internally from a Python date's
    .weekday() — never caller-supplied — so interpolating it into the SQL
    text here is safe.
    """
    with get_connection() as connection:
        rows = connection.execute(
            f"""
            SELECT service_id
            FROM gtfs_calendar
            WHERE LOWER(agency_source) = LOWER(?)
              AND start_date <= ?
              AND end_date >= ?
              AND {weekday_column} = 1
            """,
            (agency_source, gtfs_date, gtfs_date),
        ).fetchall()

    return [row["service_id"] for row in rows]


def get_calendar_date_exceptions(agency_source: str, gtfs_date: str) -> list[tuple[str, str]]:
    """
    Returns (service_id, exception_type) pairs from gtfs_calendar_dates for
    one exact date. exception_type "1" means added service that day,
    "2" means removed service that day, per the GTFS spec.
    """
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT service_id, exception_type
            FROM gtfs_calendar_dates
            WHERE LOWER(agency_source) = LOWER(?) AND date = ?
            """,
            (agency_source, gtfs_date),
        ).fetchall()

    return [(row["service_id"], row["exception_type"]) for row in rows]
