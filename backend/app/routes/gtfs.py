"""
Read-only endpoints summarizing imported GTFS data.

Unknown or unimported agency_source values (e.g. "FOO", or a real agency
that just hasn't been imported yet) return 200 with an empty list, not a
404. These are collection endpoints ("give me the routes matching this
agency"), and an empty result set is a normal, valid response for a
collection filter — the same convention GET /api/routes?city=... already
uses. A 404 is reserved for a single named resource that doesn't exist
(like GET /api/routes/{route_id}); there's no single "agency resource"
here to 404 on, and returning empty vs. 404 wouldn't change what a caller
does next, so keeping one consistent rule is simpler than adding a
second lookup query just to decide which status code to send.
"""

from datetime import date

from fastapi import APIRouter, HTTPException, Query

from app.gtfs_schemas import AgencyGtfsCounts, GtfsRouteServiceSummary, GtfsRouteWithTripCount
from app.repositories import gtfs_service_repository, gtfs_summary_repository
from app.services import gtfs_metrics

router = APIRouter(prefix="/api/gtfs", tags=["gtfs"])


@router.get("/summary", response_model=list[AgencyGtfsCounts])
def get_gtfs_summary() -> list[AgencyGtfsCounts]:
    return gtfs_summary_repository.get_summary()


@router.get("/agencies/{agency_source}/routes", response_model=list[GtfsRouteWithTripCount])
def get_agency_routes(agency_source: str) -> list[GtfsRouteWithTripCount]:
    return gtfs_summary_repository.get_routes_for_agency(agency_source)


@router.get(
    "/agencies/{agency_source}/top-routes-by-trips",
    response_model=list[GtfsRouteWithTripCount],
)
def get_agency_top_routes_by_trips(
    agency_source: str,
    limit: int = Query(default=10, ge=1, le=100),
) -> list[GtfsRouteWithTripCount]:
    return gtfs_summary_repository.get_top_routes_by_trips(agency_source, limit)


@router.get(
    "/agencies/{agency_source}/routes/{route_id}/service-summary",
    response_model=GtfsRouteServiceSummary,
)
def get_route_service_summary(
    agency_source: str,
    route_id: str,
    requested_date: date | None = Query(
        default=None,
        alias="date",
        description="Service date as YYYY-MM-DD. Defaults to today in the agency's own timezone.",
    ),
) -> GtfsRouteServiceSummary:
    """
    Unlike the list endpoints above, this names one specific route, so a
    missing agency or route_id returns 404 here — same convention already
    used by GET /api/routes/{route_id}. That's not a contradiction of the
    "empty list, not 404" rule above; it's the other half of it. Empty
    list is for "no results matched this filter," 404 is for "the one
    resource you named doesn't exist," and this endpoint is the latter.

    Headways are calculated only from service_ids actually active on the
    requested (or defaulted) date — see gtfs_metrics.compute_active_service_ids
    for why: without this, every calendar pattern the route has ever had
    (weekday, Saturday, Sunday, holidays, ...) gets pooled into one 24-hour
    window, producing a nonsensical, far-too-small headway.
    """
    route = gtfs_service_repository.get_route(agency_source, route_id)

    if route is None:
        raise HTTPException(status_code=404, detail="Route not found.")

    agency_timezone = gtfs_service_repository.get_agency_timezone(agency_source)
    service_date = gtfs_metrics.resolve_service_date(requested_date, agency_timezone)

    weekday_column = gtfs_metrics.GTFS_WEEKDAY_COLUMNS[service_date.weekday()]
    gtfs_date = service_date.strftime("%Y%m%d")  # gtfs_calendar/gtfs_calendar_dates store dates this way

    calendar_service_ids = gtfs_service_repository.get_calendar_service_ids_for_weekday(
        agency_source, weekday_column, gtfs_date
    )
    calendar_date_exceptions = gtfs_service_repository.get_calendar_date_exceptions(agency_source, gtfs_date)
    active_service_ids = gtfs_metrics.compute_active_service_ids(calendar_service_ids, calendar_date_exceptions)

    departure_times = gtfs_service_repository.get_first_stop_departure_times(
        agency_source, route_id, active_service_ids
    )
    metrics = gtfs_metrics.calculate_service_summary(departure_times)

    return GtfsRouteServiceSummary(
        **route,
        service_date=service_date.isoformat(),
        day_of_week=service_date.strftime("%A"),
        active_service_ids=active_service_ids,
        **metrics,
    )
