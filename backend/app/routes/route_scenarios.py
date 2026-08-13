from datetime import date

from fastapi import APIRouter, HTTPException, Query

from app.gtfs_schemas import GtfsServiceContext
from app.repositories import gtfs_service_repository, route_repository, scenario_gtfs_link_repository
from app.schemas import CurrentRouteMetrics, RouteComparison, RouteScenario
from app.services import gtfs_metrics
from app.services.scoring import (
    calculate_car_dependency_score,
    calculate_emissions_saved,
    calculate_transit_penalty,
    calculate_weekly_extra_transit_hours,
)
from app.services.simulator import recommend_improvement


router = APIRouter(prefix="/api/routes", tags=["routes"])


@router.get("", response_model=list[RouteScenario])
def list_routes(city: str | None = None) -> list[RouteScenario]:
    return route_repository.list_routes(city)


@router.get("/{route_id}", response_model=RouteScenario)
def get_route(route_id: int) -> RouteScenario:
    route = route_repository.get_route_by_id(route_id)

    if route is None:
        raise HTTPException(status_code=404, detail="Route not found.")

    return route


@router.get("/{route_id}/comparison", response_model=RouteComparison)
def get_route_comparison(
    route_id: int,
    requested_date: date | None = Query(
        default=None,
        alias="date",
        description=(
            "Service date as YYYY-MM-DD for any linked GTFS routes' service context. "
            "Defaults to today in each linked route's own agency timezone."
        ),
    ),
) -> RouteComparison:
    route = route_repository.get_route_by_id(route_id)

    if route is None:
        raise HTTPException(status_code=404, detail="Route not found.")

    return RouteComparison(
        route=route,
        current_metrics=CurrentRouteMetrics(
            transit_penalty=calculate_transit_penalty(route),
            car_dependency_score=calculate_car_dependency_score(route),
            weekly_extra_transit_hours=calculate_weekly_extra_transit_hours(route),
            emissions_saved_kg=calculate_emissions_saved(route),
        ),
        recommended_improvement=recommend_improvement(route),
        # route_id here is the trip_scenarios id (the app's own scenario
        # id) -- renamed to scenario_id below to avoid confusion with GTFS
        # routes' own, unrelated route_id strings.
        gtfs_service_context=_build_gtfs_service_context(scenario_id=route_id, requested_date=requested_date),
    )


def _build_gtfs_service_context(scenario_id: int, requested_date: date | None) -> list[GtfsServiceContext]:
    """
    Looks up any GTFS routes manually linked to this scenario
    (trip_scenario_gtfs_routes) and computes each one's real scheduled
    service quality for the given (or defaulted) date, using the same
    date-aware calendar logic as GET /api/gtfs/.../service-summary.

    Returns an empty list for scenarios with no link -- that's the normal
    case for most scenarios today, not an error.
    """
    contexts: list[GtfsServiceContext] = []

    for link in scenario_gtfs_link_repository.list_links_for_scenario(scenario_id):
        agency_source = link["agency_source"]
        gtfs_route_id = link["route_id"]

        gtfs_route = gtfs_service_repository.get_route(agency_source, gtfs_route_id)
        if gtfs_route is None:
            # Stale association: the linked GTFS route no longer exists
            # (e.g. after a re-import). Skip it rather than failing the
            # whole comparison.
            continue

        agency_timezone = gtfs_service_repository.get_agency_timezone(agency_source)
        service_date = gtfs_metrics.resolve_service_date(requested_date, agency_timezone)

        weekday_column = gtfs_metrics.GTFS_WEEKDAY_COLUMNS[service_date.weekday()]
        gtfs_date = service_date.strftime("%Y%m%d")

        calendar_service_ids = gtfs_service_repository.get_calendar_service_ids_for_weekday(
            agency_source, weekday_column, gtfs_date
        )
        calendar_date_exceptions = gtfs_service_repository.get_calendar_date_exceptions(agency_source, gtfs_date)
        active_service_ids = gtfs_metrics.compute_active_service_ids(calendar_service_ids, calendar_date_exceptions)

        departure_times = gtfs_service_repository.get_first_stop_departure_times(
            agency_source, gtfs_route_id, active_service_ids
        )
        metrics = gtfs_metrics.calculate_service_summary(departure_times)

        contexts.append(
            GtfsServiceContext(
                agency_source=gtfs_route["agency_source"],
                route_id=gtfs_route["route_id"],
                route_short_name=gtfs_route["route_short_name"],
                route_long_name=gtfs_route["route_long_name"],
                role=link["role"],
                service_date=service_date.isoformat(),
                average_headway_minutes=metrics["average_headway_minutes"],
                peak_headway_minutes=metrics["peak_headway_minutes"],
                midday_headway_minutes=metrics["midday_headway_minutes"],
                evening_headway_minutes=metrics["evening_headway_minutes"],
                service_span_hours=metrics["service_span_hours"],
                frequency_classification=metrics["frequency_classification"],
                explanation=gtfs_metrics.explain_service_quality(
                    metrics["frequency_classification"], metrics["service_span_hours"]
                ),
            )
        )

    return contexts
