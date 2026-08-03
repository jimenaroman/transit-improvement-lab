from app.schemas import RouteScenario


def recommend_improvement(route: RouteScenario) -> tuple[str, str]:
    if route.wait_transfer_minutes >= 30:
        return (
            "Increase service frequency",
            "14–20 min",
        )

    if route.transfers >= 2:
        return (
            "Improve transfer timing",
            "8–12 min",
        )

    if route.walking_minutes >= 15:
        return (
            "Improve stop access",
            "5–9 min",
        )

    if route.transit_minutes >= route.driving_minutes * 2:
        return (
            "Add express service",
            "15–22 min",
        )

    return (
        "Maintain current service and monitor demand",
        "0–5 min",
    )
