"""
Tests for app/services/research_analysis.py. Pure function, plain
RouteScenario objects -- no network, no DB.
"""

from app.schemas import RouteScenario
from app.services.research_analysis import build_research_summary

# Same three hand-picked routes as test_dashboard_repository.py, so the
# aggregate math can be checked on paper:
#   Route 1 (Dallas, suburb_to_downtown):  91 / 28 min -> penalty 3.25, walk 14, wait 34, transfers 2
#   Route 2 (Dallas, suburb_to_downtown):  40 / 20 min -> penalty 2.00, walk 10, wait 10, transfers 0
#   Route 3 (Chicago, campus_to_downtown): 42 / 24 min -> penalty 1.75, walk 8, wait 12, transfers 1


def _scenario(**overrides) -> RouteScenario:
    defaults = dict(
        id=1,
        city="Dallas",
        origin_label="Origin",
        destination_label="Destination",
        route_category="suburb_to_downtown",
        time_period="weekday_morning",
        distance_miles=10.0,
        driving_minutes=20,
        transit_minutes=40,
        walking_minutes=10,
        wait_transfer_minutes=10,
        transfers=0,
        fare_cost=3.0,
        gas_cost=3.0,
        driving_emissions_kg=5.0,
        transit_emissions_kg=1.0,
        notes="",
    )
    defaults.update(overrides)
    return RouteScenario(**defaults)


ROUTE_1 = _scenario(id=1, city="Dallas", route_category="suburb_to_downtown", driving_minutes=28, transit_minutes=91, walking_minutes=14, wait_transfer_minutes=34, transfers=2)
ROUTE_2 = _scenario(id=2, city="Dallas", route_category="suburb_to_downtown", driving_minutes=20, transit_minutes=40, walking_minutes=10, wait_transfer_minutes=10, transfers=0)
ROUTE_3 = _scenario(id=3, city="Chicago", route_category="campus_to_downtown", driving_minutes=24, transit_minutes=42, walking_minutes=8, wait_transfer_minutes=12, transfers=1)


def test_build_research_summary_scenario_points_include_transit_penalty():
    summary = build_research_summary([ROUTE_1, ROUTE_2, ROUTE_3])

    assert summary.scenario_count == 3
    assert [(s.id, s.transit_penalty) for s in summary.scenarios] == [(1, 3.25), (2, 2.0), (3, 1.75)]


def test_build_research_summary_overall_average():
    summary = build_research_summary([ROUTE_1, ROUTE_2, ROUTE_3])

    assert summary.overall_average_transit_penalty == 2.33  # (3.25+2.00+1.75)/3 = 2.3333...


def test_build_research_summary_average_by_city():
    summary = build_research_summary([ROUTE_1, ROUTE_2, ROUTE_3])
    by_city = {row.city: row.average_transit_penalty for row in summary.average_transit_penalty_by_city}

    assert by_city["Dallas"] == 2.62  # (3.25+2.00)/2 = 2.625 -> round-half-to-even
    assert by_city["Chicago"] == 1.75


def test_build_research_summary_average_by_category_sorted_worst_first():
    summary = build_research_summary([ROUTE_1, ROUTE_2, ROUTE_3])

    assert [row.route_category for row in summary.average_transit_penalty_by_category] == [
        "suburb_to_downtown",  # 2.625 average -- worse
        "campus_to_downtown",  # 1.75 average
    ]


def test_build_research_summary_empty_scenarios():
    summary = build_research_summary([])

    assert summary.scenario_count == 0
    assert summary.overall_average_transit_penalty == 0.0
    assert summary.scenarios == []
    assert summary.average_transit_penalty_by_city == []
    assert summary.average_transit_penalty_by_category == []
    assert summary.correlations.walking_minutes_vs_transit_penalty is None
    assert summary.correlations.wait_transfer_minutes_vs_transit_penalty is None
    assert summary.correlations.transfers_vs_transit_penalty is None


def test_correlation_perfect_positive_relationship():
    # driving_minutes fixed at 10 for all three -> penalty is exactly
    # transit_minutes / 10, so walking_minutes tracks penalty perfectly.
    routes = [
        _scenario(id=1, driving_minutes=10, transit_minutes=10, walking_minutes=5),
        _scenario(id=2, driving_minutes=10, transit_minutes=20, walking_minutes=10),
        _scenario(id=3, driving_minutes=10, transit_minutes=30, walking_minutes=15),
    ]

    summary = build_research_summary(routes)

    assert summary.correlations.walking_minutes_vs_transit_penalty == 1.0


def test_correlation_none_when_column_has_zero_variance():
    # transfers is 1 for every route -- no variance, so correlating it
    # against transit_penalty is undefined rather than a guessed number.
    routes = [
        _scenario(id=1, driving_minutes=10, transit_minutes=10, transfers=1),
        _scenario(id=2, driving_minutes=10, transit_minutes=20, transfers=1),
        _scenario(id=3, driving_minutes=10, transit_minutes=30, transfers=1),
    ]

    summary = build_research_summary(routes)

    assert summary.correlations.transfers_vs_transit_penalty is None


def test_correlation_none_with_fewer_than_two_scenarios():
    summary = build_research_summary([ROUTE_1])

    assert summary.correlations.walking_minutes_vs_transit_penalty is None


def test_build_research_summary_assigns_a_bottleneck_category_per_scenario():
    summary = build_research_summary([ROUTE_1, ROUTE_2, ROUTE_3])

    categories = {s.id: s.bottleneck_category for s in summary.scenarios}
    assert categories[1] == "transfer_burden"  # 2 transfers
    assert categories[2] == "competitive"  # nothing crosses a threshold
    assert categories[3] == "transfer_coordination"  # 12 min wait over 1 transfer


def test_build_research_summary_bottleneck_distribution_counts_and_sorts():
    summary = build_research_summary([ROUTE_1, ROUTE_2, ROUTE_3])

    counts = {row.category: row.count for row in summary.bottleneck_distribution}
    assert counts == {"transfer_burden": 1, "competitive": 1, "transfer_coordination": 1}
    assert sum(counts.values()) == 3


def test_build_research_summary_empty_scenarios_has_empty_bottleneck_distribution():
    summary = build_research_summary([])

    assert summary.bottleneck_distribution == []
