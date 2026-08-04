from fastapi import APIRouter, HTTPException

from app.repositories import route_repository
from app.schemas import CurrentRouteMetrics, RouteComparison, RouteScenario
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
def get_route_comparison(route_id: int) -> RouteComparison:
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
    )
