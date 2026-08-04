from pydantic import BaseModel


class RouteScenario(BaseModel):
    id: int
    city: str
    origin_label: str
    destination_label: str
    route_category: str
    time_period: str
    distance_miles: float
    driving_minutes: int
    transit_minutes: int
    walking_minutes: int
    wait_transfer_minutes: int
    transfers: int
    fare_cost: float
    gas_cost: float
    driving_emissions_kg: float
    transit_emissions_kg: float
    notes: str


class RecommendedImprovement(BaseModel):
    title: str
    category: str
    minutes_saved: int
    savings_source: str
    new_transit_minutes: int
    new_transit_penalty: float
    verdict: str
    explanation: str


class CurrentRouteMetrics(BaseModel):
    transit_penalty: float
    car_dependency_score: int
    weekly_extra_transit_hours: float
    emissions_saved_kg: float


class RouteComparison(BaseModel):
    route: RouteScenario
    current_metrics: CurrentRouteMetrics
    recommended_improvement: RecommendedImprovement


class CityTransitPenalty(BaseModel):
    city: str
    average_transit_penalty: float


class CityWaitTransferMinutes(BaseModel):
    city: str
    average_wait_transfer_minutes: float


class WorstRouteByTransitPenalty(BaseModel):
    id: int
    city: str
    origin_label: str
    destination_label: str
    transit_penalty: float


class WorstRouteByWaitTransferMinutes(BaseModel):
    id: int
    city: str
    origin_label: str
    destination_label: str
    wait_transfer_minutes: int


class RouteCategoryCount(BaseModel):
    route_category: str
    count: int


class DashboardSummary(BaseModel):
    total_routes: int
    average_transit_penalty: float
    average_transit_penalty_by_city: list[CityTransitPenalty]
    worst_route_by_transit_penalty: WorstRouteByTransitPenalty | None
    worst_route_by_wait_transfer_minutes: WorstRouteByWaitTransferMinutes | None
    average_wait_transfer_minutes_by_city: list[CityWaitTransferMinutes]
    route_count_by_category: list[RouteCategoryCount]
