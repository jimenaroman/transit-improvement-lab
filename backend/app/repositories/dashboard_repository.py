"""
Repository for dashboard summary queries.

Like route_repository.py, this is the only place that writes SQL for these
queries. Each function runs one SQL aggregate query against trip_scenarios
(AVG, COUNT, GROUP BY, or ORDER BY ... LIMIT 1 for "worst route") instead of
pulling every row into Python and computing the summary there — SQLite is
already good at this, so we let it do the work.

transit_penalty isn't a stored column; it's transit_minutes divided by
driving_minutes, so every penalty-related query computes it inline with
CAST(transit_minutes AS REAL) / driving_minutes. The CAST forces floating
point division — without it, SQLite would do integer division and silently
truncate (e.g. 91 / 28 would come out to 3, not 3.25).
"""

from app.database import get_connection
from app.schemas import (
    CityTransitPenalty,
    CityWaitTransferMinutes,
    DashboardSummary,
    RouteCategoryCount,
    WorstRouteByTransitPenalty,
    WorstRouteByWaitTransferMinutes,
)

TRANSIT_PENALTY_SQL = "CAST(transit_minutes AS REAL) / driving_minutes"


def count_routes() -> int:
    with get_connection() as connection:
        row = connection.execute("SELECT COUNT(*) AS total FROM trip_scenarios").fetchone()

    return row["total"]


def average_transit_penalty() -> float | None:
    with get_connection() as connection:
        row = connection.execute(
            f"SELECT AVG({TRANSIT_PENALTY_SQL}) AS average FROM trip_scenarios"
        ).fetchone()

    return round(row["average"], 2) if row["average"] is not None else None


def average_transit_penalty_by_city() -> list[CityTransitPenalty]:
    with get_connection() as connection:
        rows = connection.execute(
            f"""
            SELECT city, AVG({TRANSIT_PENALTY_SQL}) AS average_transit_penalty
            FROM trip_scenarios
            GROUP BY city
            ORDER BY city
            """
        ).fetchall()

    return [
        CityTransitPenalty(city=row["city"], average_transit_penalty=round(row["average_transit_penalty"], 2))
        for row in rows
    ]


def average_wait_transfer_minutes_by_city() -> list[CityWaitTransferMinutes]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT city, AVG(wait_transfer_minutes) AS average_wait_transfer_minutes
            FROM trip_scenarios
            GROUP BY city
            ORDER BY city
            """
        ).fetchall()

    return [
        CityWaitTransferMinutes(
            city=row["city"],
            average_wait_transfer_minutes=round(row["average_wait_transfer_minutes"], 1),
        )
        for row in rows
    ]


def worst_route_by_transit_penalty() -> WorstRouteByTransitPenalty | None:
    with get_connection() as connection:
        row = connection.execute(
            f"""
            SELECT id, city, origin_label, destination_label, {TRANSIT_PENALTY_SQL} AS transit_penalty
            FROM trip_scenarios
            ORDER BY transit_penalty DESC
            LIMIT 1
            """
        ).fetchone()

    if row is None:
        return None

    return WorstRouteByTransitPenalty(
        id=row["id"],
        city=row["city"],
        origin_label=row["origin_label"],
        destination_label=row["destination_label"],
        transit_penalty=round(row["transit_penalty"], 2),
    )


def worst_route_by_wait_transfer_minutes() -> WorstRouteByWaitTransferMinutes | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT id, city, origin_label, destination_label, wait_transfer_minutes
            FROM trip_scenarios
            ORDER BY wait_transfer_minutes DESC
            LIMIT 1
            """
        ).fetchone()

    return WorstRouteByWaitTransferMinutes(**dict(row)) if row is not None else None


def route_count_by_category() -> list[RouteCategoryCount]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT route_category, COUNT(*) AS count
            FROM trip_scenarios
            GROUP BY route_category
            ORDER BY count DESC, route_category
            """
        ).fetchall()

    return [RouteCategoryCount(route_category=row["route_category"], count=row["count"]) for row in rows]


def get_summary() -> DashboardSummary:
    return DashboardSummary(
        total_routes=count_routes(),
        average_transit_penalty=average_transit_penalty() or 0.0,
        average_transit_penalty_by_city=average_transit_penalty_by_city(),
        worst_route_by_transit_penalty=worst_route_by_transit_penalty(),
        worst_route_by_wait_transfer_minutes=worst_route_by_wait_transfer_minutes(),
        average_wait_transfer_minutes_by_city=average_wait_transfer_minutes_by_city(),
        route_count_by_category=route_count_by_category(),
    )
