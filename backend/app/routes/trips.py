"""
POST /api/trips/compare -- arbitrary origin/destination trip comparison via
Google Routes, with real GTFS enrichment where a transit line can be
matched unambiguously. See docs/google-routes-integration.md.
"""

from datetime import date

from fastapi import APIRouter, HTTPException

from app.clients.google_routes_client import GoogleRoutesApiError, fetch_drive_route, fetch_transit_route
from app.repositories import gtfs_service_repository
from app.services import gtfs_metrics
from app.services.trip_bottleneck_analysis import classify_bottlenecks, recommend_improvements
from app.services.trip_comparison import (
    TripComparisonError,
    build_trip_verdict,
    calculate_trip_transit_penalty,
    extract_transit_lines,
    normalize_drive_route,
    normalize_transit_route,
    resolve_representative_departure_time,
)
from app.trip_compare_schemas import TripCompareRequest, TripCompareResponse, TripGtfsServiceContext

router = APIRouter(prefix="/api/trips", tags=["trips"])


@router.post("/compare", response_model=TripCompareResponse)
def compare_trip(request: TripCompareRequest) -> TripCompareResponse:
    # A fixed representative weekday-daytime departure, not "now" -- see
    # resolve_representative_departure_time's docstring. Anchors both the
    # Google TRANSIT call and the GTFS service-date lookup below to the
    # same moment, so they describe the same hypothetical trip.
    departure_time = resolve_representative_departure_time()

    try:
        drive_raw = fetch_drive_route(request.origin, request.destination)
        transit_raw = fetch_transit_route(request.origin, request.destination, departure_time)
    except GoogleRoutesApiError as error:
        # Generic message only -- never surface the underlying error text,
        # which could echo request details, to keep this response minimal.
        raise HTTPException(status_code=502, detail="Could not reach the routing service.") from error

    try:
        driving = normalize_drive_route(drive_raw)
        transit = normalize_transit_route(transit_raw)
        transit_penalty = calculate_trip_transit_penalty(transit.duration_minutes, driving.duration_minutes)
    except TripComparisonError:
        raise HTTPException(
            status_code=404, detail="No usable route found between the given origin and destination."
        ) from None

    gtfs_service_context = _build_trip_gtfs_service_context(transit_raw, departure_time.date())
    extra_minutes = transit.duration_minutes - driving.duration_minutes

    bottlenecks = classify_bottlenecks(transit, driving, transit_penalty, gtfs_service_context)

    return TripCompareResponse(
        origin=request.origin.label,
        destination=request.destination.label,
        departure_time=departure_time.isoformat(),
        driving=driving,
        transit=transit,
        gtfs_service_context=gtfs_service_context,
        comparison={
            "transit_penalty": transit_penalty,
            "extra_minutes": extra_minutes,
            "verdict": build_trip_verdict(extra_minutes),
        },
        bottlenecks=bottlenecks,
        recommendations=recommend_improvements(bottlenecks),
    )


def _build_trip_gtfs_service_context(transit_raw: dict, service_date: date) -> list[TripGtfsServiceContext]:
    """
    Mirrors route_scenarios.py's _build_gtfs_service_context, but the
    route to enrich is discovered by name-matching a Google transit line
    instead of a curated trip_scenario_gtfs_routes link.
    """
    contexts: list[TripGtfsServiceContext] = []

    for line in extract_transit_lines(transit_raw):
        agency_source = (
            gtfs_service_repository.get_agency_source_by_name(line["agency_name"]) if line["agency_name"] else None
        )

        if agency_source is None:
            contexts.append(
                _unmatched_context(line, reason="Agency not recognized among imported GTFS feeds.")
            )
            continue

        candidates = gtfs_service_repository.find_candidate_routes_by_name(
            agency_source, line["route_short_name"], line["route_long_name"]
        )

        if len(candidates) != 1:
            reason = "No matching GTFS route found." if not candidates else "Multiple GTFS routes matched; not guessing."
            contexts.append(_unmatched_context(line, agency_source=agency_source, reason=reason))
            continue

        gtfs_route = candidates[0]
        contexts.append(_matched_context(gtfs_route, service_date))

    return contexts


def _unmatched_context(
    line: dict, reason: str, agency_source: str | None = None
) -> TripGtfsServiceContext:
    return TripGtfsServiceContext(
        agency_source=agency_source,
        route_short_name=line["route_short_name"],
        route_long_name=line["route_long_name"],
        route_id=None,
        average_headway_minutes=None,
        frequency_classification=None,
        service_span_hours=None,
        explanation=None,
        matched=False,
        unmatched_reason=reason,
    )


def _matched_context(gtfs_route: dict, service_date: date) -> TripGtfsServiceContext:
    agency_source = gtfs_route["agency_source"]
    route_id = gtfs_route["route_id"]

    weekday_column = gtfs_metrics.GTFS_WEEKDAY_COLUMNS[service_date.weekday()]
    gtfs_date = service_date.strftime("%Y%m%d")

    calendar_service_ids = gtfs_service_repository.get_calendar_service_ids_for_weekday(
        agency_source, weekday_column, gtfs_date
    )
    calendar_date_exceptions = gtfs_service_repository.get_calendar_date_exceptions(agency_source, gtfs_date)
    active_service_ids = gtfs_metrics.compute_active_service_ids(calendar_service_ids, calendar_date_exceptions)

    departure_times = gtfs_service_repository.get_first_stop_departure_times(
        agency_source, route_id, active_service_ids
    )
    metrics = gtfs_metrics.calculate_service_summary(departure_times)

    return TripGtfsServiceContext(
        agency_source=agency_source,
        route_short_name=gtfs_route["route_short_name"],
        route_long_name=gtfs_route["route_long_name"],
        route_id=route_id,
        average_headway_minutes=metrics["average_headway_minutes"],
        frequency_classification=metrics["frequency_classification"],
        service_span_hours=metrics["service_span_hours"],
        explanation=gtfs_metrics.explain_service_quality(
            metrics["frequency_classification"], metrics["service_span_hours"]
        ),
        matched=True,
        unmatched_reason=None,
    )
