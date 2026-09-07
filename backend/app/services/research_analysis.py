"""
Lightweight aggregation/correlation layer over the curated trip_scenarios
sample, for the Research page. Pure functions only -- callers fetch the
routes and pass them in, nothing here touches the database.

This is exploratory analysis of a small (12-scenario) curated sample, not a
statistical model. Every figure is derived directly from real scenario
fields; nothing here is invented or estimated.
"""

import statistics
from collections import defaultdict

from app.schemas import (
    CategoryTransitPenalty,
    CityTransitPenalty,
    ResearchCorrelations,
    ResearchScenarioPoint,
    ResearchSummary,
    RouteScenario,
)
from app.services.scoring import calculate_transit_penalty


def _pearson_correlation(xs: list[float], ys: list[float]) -> float | None:
    """None when there's too little data or no variance to correlate -- never a guessed value."""
    if len(xs) < 2:
        return None
    try:
        return round(statistics.correlation(xs, ys), 2)
    except statistics.StatisticsError:
        return None


def _average_transit_penalty_by(
    routes: list[RouteScenario], penalties: list[float], key: str
) -> list[tuple[str, float]]:
    grouped: dict[str, list[float]] = defaultdict(list)
    for route, penalty in zip(routes, penalties):
        grouped[getattr(route, key)].append(penalty)

    return [(group, round(statistics.mean(values), 2)) for group, values in grouped.items()]


def build_research_summary(routes: list[RouteScenario]) -> ResearchSummary:
    penalties = [calculate_transit_penalty(route) for route in routes]

    by_city = sorted(_average_transit_penalty_by(routes, penalties, "city"))
    by_category = sorted(
        _average_transit_penalty_by(routes, penalties, "route_category"),
        key=lambda entry: entry[1],
        reverse=True,
    )

    return ResearchSummary(
        scenario_count=len(routes),
        overall_average_transit_penalty=round(statistics.mean(penalties), 2) if penalties else 0.0,
        average_transit_penalty_by_city=[
            CityTransitPenalty(city=city, average_transit_penalty=average) for city, average in by_city
        ],
        average_transit_penalty_by_category=[
            CategoryTransitPenalty(route_category=category, average_transit_penalty=average)
            for category, average in by_category
        ],
        scenarios=[
            ResearchScenarioPoint(
                id=route.id,
                city=route.city,
                origin_label=route.origin_label,
                destination_label=route.destination_label,
                route_category=route.route_category,
                walking_minutes=route.walking_minutes,
                wait_transfer_minutes=route.wait_transfer_minutes,
                transfers=route.transfers,
                transit_penalty=penalty,
            )
            for route, penalty in zip(routes, penalties)
        ],
        correlations=ResearchCorrelations(
            walking_minutes_vs_transit_penalty=_pearson_correlation(
                [route.walking_minutes for route in routes], penalties
            ),
            wait_transfer_minutes_vs_transit_penalty=_pearson_correlation(
                [route.wait_transfer_minutes for route in routes], penalties
            ),
            transfers_vs_transit_penalty=_pearson_correlation([route.transfers for route in routes], penalties),
        ),
    )
