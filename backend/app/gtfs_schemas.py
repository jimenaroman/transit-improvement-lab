"""
Response schemas for the GTFS summary API (/api/gtfs/...).

Kept separate from schemas.py because these describe imported transit
schedule data (the gtfs_* tables), not the app's own manual route
scenarios in trip_scenarios.
"""

from pydantic import BaseModel


class AgencyGtfsCounts(BaseModel):
    agency_source: str
    routes: int
    stops: int
    trips: int
    stop_times: int
    calendar: int
    calendar_dates: int


class GtfsRouteWithTripCount(BaseModel):
    route_id: str
    route_short_name: str | None
    route_long_name: str | None
    route_type: str | None
    trip_count: int


class GtfsRouteServiceSummary(BaseModel):
    agency_source: str
    route_id: str
    route_short_name: str | None
    route_long_name: str | None
    route_type: str | None
    service_date: str
    day_of_week: str
    active_service_ids: list[str]
    trip_count: int
    first_departure_time: str | None
    last_departure_time: str | None
    average_headway_minutes: float | None
    peak_headway_minutes: float | None
    midday_headway_minutes: float | None
    evening_headway_minutes: float | None
    service_span_hours: float | None
    frequency_classification: str


class GtfsServiceContext(BaseModel):
    """
    Real scheduled-service evidence for one GTFS route manually linked to
    a trip_scenarios row (see trip_scenario_gtfs_routes). Attached to
    GET /api/routes/{route_id}/comparison responses -- see schemas.py's
    RouteComparison.
    """

    agency_source: str
    route_id: str
    route_short_name: str | None
    route_long_name: str | None
    role: str | None
    service_date: str
    average_headway_minutes: float | None
    peak_headway_minutes: float | None
    midday_headway_minutes: float | None
    evening_headway_minutes: float | None
    service_span_hours: float | None
    frequency_classification: str
    explanation: str
