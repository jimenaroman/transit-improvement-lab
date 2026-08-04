"""
V1 heuristic improvement simulator.

Given a route scenario, picks the single biggest time burden (wait/transfer
time, transfer count, walking, or an overall transit-vs-driving gap) and
estimates the effect of one targeted improvement addressing it. The
before/after numbers are illustrative planning estimates for comparing
intervention types, not validated transit engineering projections. The
constants below are initial assumptions and should later be tuned using
real route data, user research, or transportation literature.
"""

from app.schemas import RecommendedImprovement, RouteScenario
from app.services.scoring import calculate_transit_penalty

WAIT_TRANSFER_TRIGGER_MINUTES = 30
TRANSFERS_TRIGGER = 2
WALKING_TRIGGER_MINUTES = 15
EXPRESS_TRANSIT_MULTIPLIER = 2

BASELINE_HEADWAY_MINUTES = 30
IMPROVED_HEADWAY_MINUTES = 15
TRANSFER_COORDINATION_SAVINGS_PER_TRANSFER = 5
WALKING_ACCESS_SAVINGS_MINUTES = 7
EXPRESS_SERVICE_SAVINGS_FRACTION = 0.2

COMPETITIVE_GAP_MINUTES = 10


def _plan_improvement(route: RouteScenario) -> tuple[str, str, str, int, str]:
    """Returns (title, category, savings_source, minutes_saved, burden_description)."""

    if route.wait_transfer_minutes >= WAIT_TRANSFER_TRIGGER_MINUTES:
        wait_points = max(route.transfers, 1)
        per_point_savings = (BASELINE_HEADWAY_MINUTES - IMPROVED_HEADWAY_MINUTES) / 2
        minutes_saved = min(round(per_point_savings * wait_points), route.wait_transfer_minutes)
        return (
            f"Improve headways from {BASELINE_HEADWAY_MINUTES} min to {IMPROVED_HEADWAY_MINUTES} min",
            "frequency",
            f"Reduced average wait time across {wait_points} waiting point(s)",
            minutes_saved,
            f"This route loses {route.wait_transfer_minutes} minutes to waiting and transfers.",
        )

    if route.transfers >= TRANSFERS_TRIGGER:
        minutes_saved = min(
            TRANSFER_COORDINATION_SAVINGS_PER_TRANSFER * route.transfers,
            route.wait_transfer_minutes,
        )
        return (
            "Improve transfer timing and coordination",
            "transfer_coordination",
            f"Reduced average transfer wait across {route.transfers} transfers",
            minutes_saved,
            f"This route requires {route.transfers} transfers, adding wait and coordination time.",
        )

    if route.walking_minutes >= WALKING_TRIGGER_MINUTES:
        minutes_saved = min(WALKING_ACCESS_SAVINGS_MINUTES, route.walking_minutes)
        return (
            "Improve stop access and pedestrian routes",
            "stop_access",
            "Reduced walking time to and from stops",
            minutes_saved,
            f"This route requires {route.walking_minutes} minutes of walking to reach transit.",
        )

    if route.transit_minutes >= route.driving_minutes * EXPRESS_TRANSIT_MULTIPLIER:
        minutes_saved = round(route.transit_minutes * EXPRESS_SERVICE_SAVINGS_FRACTION)
        return (
            "Add express or limited-stop service",
            "express_service",
            "Fewer stops between origin and destination",
            minutes_saved,
            (
                f"This route takes {route.transit_minutes} minutes by transit versus "
                f"{route.driving_minutes} minutes by car, with no express alternative."
            ),
        )

    return (
        "Maintain current service and monitor demand",
        "monitor",
        "No dominant time burden identified",
        0,
        "",
    )


def recommend_improvement(route: RouteScenario) -> RecommendedImprovement:
    title, category, savings_source, minutes_saved, burden_description = _plan_improvement(route)

    # An improvement can't make transit faster than driving on its own.
    minutes_saved = min(minutes_saved, max(route.transit_minutes - route.driving_minutes, 0))

    current_transit_penalty = calculate_transit_penalty(route)
    new_transit_minutes = route.transit_minutes - minutes_saved
    new_transit_penalty = round(new_transit_minutes / route.driving_minutes, 2)
    gap = new_transit_minutes - route.driving_minutes

    if minutes_saved <= 0:
        verdict = "No dominant time burden identified"
        explanation = "This route does not have a single dominant time burden, so no targeted improvement is simulated yet."
    elif gap <= COMPETITIVE_GAP_MINUTES:
        verdict = "Meaningful improvement — transit becomes roughly competitive with driving"
        explanation = (
            f"{burden_description} {title} could save about {minutes_saved} minutes, "
            f"cutting the transit penalty from {current_transit_penalty}x to {new_transit_penalty}x. "
            "Transit becomes roughly competitive with driving time."
        )
    else:
        verdict = "Helpful, but route remains car-dependent"
        explanation = (
            f"{burden_description} {title} could save about {minutes_saved} minutes, "
            f"cutting the transit penalty from {current_transit_penalty}x to {new_transit_penalty}x. "
            f"Transit would still take {gap} minutes longer than driving; this route likely "
            "needs a bigger intervention, such as express service or a more direct route."
        )

    return RecommendedImprovement(
        title=title,
        category=category,
        minutes_saved=minutes_saved,
        savings_source=savings_source,
        new_transit_minutes=new_transit_minutes,
        new_transit_penalty=new_transit_penalty,
        verdict=verdict,
        explanation=explanation,
    )
