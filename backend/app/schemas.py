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


class RouteComparison(BaseModel):
    route: RouteScenario
    transit_penalty: float
    car_dependency_score: int
    weekly_extra_transit_hours: float
    emissions_saved_kg: float
    recommended_improvement: str
    estimated_minutes_saved: str
