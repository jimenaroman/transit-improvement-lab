"""
Request/response schemas for POST /api/trips/compare and
GET /api/places/autocomplete. Deliberately separate from schemas.py's
RouteScenario/RouteComparison -- those describe a curated trip_scenarios
row (fare, emissions, city, ...), fields an arbitrary Google-routed trip
doesn't have. See docs/google-routes-integration.md.
"""

from pydantic import BaseModel, model_validator


class LocationInput(BaseModel):
    """
    label is always the display text (what the user typed or saw in an
    autocomplete suggestion). place_id, when present, is the stable
    identifier from a selected autocomplete suggestion and is what
    actually gets routed -- label alone is the fallback for someone who
    types an address and never opens the suggestion list.
    """

    label: str
    place_id: str | None = None

    @model_validator(mode="after")
    def _label_not_blank(self) -> "LocationInput":
        if not self.label.strip():
            raise ValueError("label must not be blank.")
        return self


class TripCompareRequest(BaseModel):
    origin: LocationInput
    destination: LocationInput


class DrivingSummary(BaseModel):
    duration_minutes: int
    distance_miles: float | None
    polyline: str | None


class TripRouteSegment(BaseModel):
    """One step of the transit itinerary, for map rendering only -- travel_mode
    is Google's own value ("WALK" or "TRANSIT"), never inferred or guessed.
    polyline is None on the rare step Google didn't return one for."""

    travel_mode: str
    polyline: str | None


class TripItineraryLeg(BaseModel):
    """
    One rider-facing leg of the trip: a walk to/from transit, a ride on one
    named line, or a wait/transfer between two rides. Unlike TripRouteSegment
    (one per raw Google step, for the map), consecutive walk steps are
    merged and each wait is its own leg -- computed from real stop
    arrival/departure timestamps, not from any step's own duration, since
    Google doesn't return waiting time as a step. duration_minutes is None
    only when a wait couldn't be computed (a missing timestamp), never a
    guessed number.
    """

    kind: str  # "walk", "ride", or "wait"
    label: str
    duration_minutes: int | None


class TransitSummary(BaseModel):
    duration_minutes: int
    distance_miles: float | None
    walking_minutes: int
    transfers: int
    route_names: list[str]
    polyline: str | None
    segments: list[TripRouteSegment]
    itinerary: list[TripItineraryLeg]


class TripGtfsServiceContext(BaseModel):
    """
    One Google transit line, optionally enriched with real GTFS service
    data. matched=False means no confident gtfs_routes match was found --
    the line still appears here so the caller knows it was considered, but
    every *_headway/frequency/span field is None rather than guessed.
    """

    agency_source: str | None
    route_short_name: str | None
    route_long_name: str | None
    route_id: str | None
    average_headway_minutes: float | None
    frequency_classification: str | None
    service_span_hours: float | None
    explanation: str | None
    matched: bool
    unmatched_reason: str | None


class TripComparisonMetrics(BaseModel):
    transit_penalty: float
    extra_minutes: int
    verdict: str


class TripCompareResponse(BaseModel):
    origin: str
    destination: str
    departure_time: str
    driving: DrivingSummary
    transit: TransitSummary
    gtfs_service_context: list[TripGtfsServiceContext]
    comparison: TripComparisonMetrics


class PlaceSuggestion(BaseModel):
    """label is a ready-to-use display string ("primary, secondary") so the
    frontend has one value to show and to send back as a LocationInput.label
    -- it doesn't need to reassemble primary_text/secondary_text itself."""

    label: str
    place_id: str
    primary_text: str
    secondary_text: str | None
