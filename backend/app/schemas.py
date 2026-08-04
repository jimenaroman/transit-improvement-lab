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
    current_transit_minutes: int
    new_transit_minutes: int
    current_transit_penalty: float
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
