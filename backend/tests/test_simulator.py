from app.schemas import RouteScenario
from app.services.simulator import recommend_improvement

DALLAS_ROUTE = RouteScenario(
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


def test_frequency_improvement_matches_worked_example():
    improvement = recommend_improvement(DALLAS_ROUTE)

    assert improvement.category == "frequency"
    assert improvement.minutes_saved == 15
    assert improvement.current_transit_minutes == 91
    assert improvement.new_transit_minutes == 76
    assert improvement.current_transit_penalty == 3.25
    assert improvement.new_transit_penalty == 2.71
    assert improvement.verdict == "Helpful, but route remains car-dependent"


def test_monitor_when_no_dominant_burden():
    easy_route = DALLAS_ROUTE.model_copy(
        update={
            "wait_transfer_minutes": 5,
            "transfers": 0,
            "walking_minutes": 5,
            "transit_minutes": 30,
            "driving_minutes": 28,
        }
    )

    improvement = recommend_improvement(easy_route)

    assert improvement.category == "monitor"
    assert improvement.minutes_saved == 0
    assert improvement.new_transit_minutes == 30
