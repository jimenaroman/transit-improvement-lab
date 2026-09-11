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
    BottleneckCategoryCount,
    CategoryTransitPenalty,
    CityTransitPenalty,
    ResearchCorrelations,
    ResearchScenarioPoint,
    ResearchSummary,
    RouteScenario,
)
from app.services.scoring import calculate_transit_penalty
from app.services.trip_bottleneck_analysis import classify_bottlenecks_from_metrics


def _primary_bottleneck_category(route: RouteScenario, transit_penalty: float) -> str:
    """
    The first (highest-priority) triggered category for this curated
    scenario. frequency_classification is always None here -- this sample's
    aggregate view doesn't join live per-scenario GTFS data, so
    service_frequency/route_directness simply won't fire; the other
    categories still work from the scenario's own stored fields.
    """
    findings = classify_bottlenecks_from_metrics(
        walking_minutes=route.walking_minutes,
        wait_minutes=route.wait_transfer_minutes,
        transit_minutes=route.transit_minutes,
        driving_minutes=route.driving_minutes,
        transfers=route.transfers,
        transit_penalty=transit_penalty,
        frequency_classification=None,
        average_headway_minutes=None,
    )
    return findings[0].category


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
    bottleneck_categories = [_primary_bottleneck_category(route, penalty) for route, penalty in zip(routes, penalties)]

    by_city = sorted(_average_transit_penalty_by(routes, penalties, "city"))
    by_category = sorted(
        _average_transit_penalty_by(routes, penalties, "route_category"),
        key=lambda entry: entry[1],
        reverse=True,
    )
    bottleneck_counts: dict[str, int] = defaultdict(int)
    for category in bottleneck_categories:
        bottleneck_counts[category] += 1
    bottleneck_distribution = sorted(
        (BottleneckCategoryCount(category=category, count=count) for category, count in bottleneck_counts.items()),
        key=lambda entry: entry.count,
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
                bottleneck_category=category,
            )
            for route, penalty, category in zip(routes, penalties, bottleneck_categories)
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
        bottleneck_distribution=bottleneck_distribution,
    )
