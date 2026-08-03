"""
V1 heuristic scoring model.

This score is not a validated urban planning metric yet. It is an
interpretable prototype score that combines four route burdens:
1. How much slower transit is than driving
2. How much time is spent waiting/transferring
3. How many transfers are required
4. How much walking is required

The constants below are initial assumptions and should later be tuned
using real route data, user research, or transportation literature.
"""

from app.schemas import RouteScenario

MAX_TRANSIT_PENALTY = 4.0
MAX_WAIT_TRANSFER_MINUTES = 45
MAX_TRANSFERS = 3
MAX_WALKING_MINUTES = 30

TRANSIT_PENALTY_WEIGHT = 40
WAIT_TRANSFER_WEIGHT = 25
TRANSFER_WEIGHT = 20
WALKING_WEIGHT = 15


def calculate_transit_penalty(route: RouteScenario) -> float:
    if route.driving_minutes <= 0:
        raise ValueError("Driving minutes must be greater than zero.")

    return round(route.transit_minutes / route.driving_minutes, 2)


def calculate_car_dependency_score(route: RouteScenario) -> int:
    transit_penalty = calculate_transit_penalty(route)

    penalty_score = min(transit_penalty / MAX_TRANSIT_PENALTY, 1) * TRANSIT_PENALTY_WEIGHT
    wait_score = min(route.wait_transfer_minutes / MAX_WAIT_TRANSFER_MINUTES, 1) * WAIT_TRANSFER_WEIGHT
    transfer_score = min(route.transfers / MAX_TRANSFERS, 1) * TRANSFER_WEIGHT
    walking_score = min(route.walking_minutes / MAX_WALKING_MINUTES, 1) * WALKING_WEIGHT

    total_score = penalty_score + wait_score + transfer_score + walking_score

    return round(total_score)


def calculate_weekly_extra_transit_hours(route: RouteScenario, round_trips_per_week: int = 5) -> float:
    one_way_difference = route.transit_minutes - route.driving_minutes
    weekly_extra_minutes = one_way_difference * 2 * round_trips_per_week

    return round(weekly_extra_minutes / 60, 1)


def calculate_emissions_saved(route: RouteScenario) -> float:
    return round(route.driving_emissions_kg - route.transit_emissions_kg, 2)
