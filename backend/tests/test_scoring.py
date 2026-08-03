from app.schemas import RouteScenario
from app.services.scoring import calculate_car_dependency_score, calculate_transit_penalty


def test_calculate_transit_penalty():
    route = RouteScenario(
        id=1,
        city="Dallas",
        origin_label="Dallas suburb",
        destination_label="Downtown Dallas",
        route_category="suburb_to_downtown",
        time_period="weekday_morning",
        distance_miles=15.2,
        driving_minutes=28,
        transit_minutes=91,
        walking_minutes=14,
        wait_transfer_minutes=34,
        transfers=2,
        fare_cost=3.0,
        gas_cost=3.75,
        driving_emissions_kg=6.2,
        transit_emissions_kg=1.4,
        notes="Test route.",
    )

    assert calculate_transit_penalty(route) == 3.25


def test_car_dependency_score_is_between_0_and_100():
    route = RouteScenario(
        id=1,
        city="Dallas",
        origin_label="Dallas suburb",
        destination_label="Downtown Dallas",
        route_category="suburb_to_downtown",
        time_period="weekday_morning",
        distance_miles=15.2,
        driving_minutes=28,
        transit_minutes=91,
        walking_minutes=14,
        wait_transfer_minutes=34,
        transfers=2,
        fare_cost=3.0,
        gas_cost=3.75,
        driving_emissions_kg=6.2,
        transit_emissions_kg=1.4,
        notes="Test route.",
    )

    score = calculate_car_dependency_score(route)

    assert 0 <= score <= 100
