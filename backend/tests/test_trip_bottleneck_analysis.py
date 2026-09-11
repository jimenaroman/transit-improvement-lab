"""
Tests for app/services/trip_bottleneck_analysis.py. Plain TransitSummary/
DrivingSummary/TripGtfsServiceContext objects in, no network, no DB -- each
test isolates exactly one trigger rule by holding every other input at a
"clean" baseline that shouldn't trigger anything else.
"""

from app.services.trip_bottleneck_analysis import (
    classify_bottlenecks,
    recommend_improvements,
    worst_matched_gtfs_context,
)
from app.trip_compare_schemas import DrivingSummary, TransitSummary, TripGtfsServiceContext

DRIVING = DrivingSummary(duration_minutes=20, distance_miles=10.0, polyline=None)


def _transit(**overrides) -> TransitSummary:
    defaults = dict(
        duration_minutes=25,
        distance_miles=10.0,
        walking_minutes=3,
        riding_minutes=20,
        wait_minutes=0,
        transfers=0,
        route_names=[],
        polyline=None,
        segments=[],
        itinerary=[],
    )
    defaults.update(overrides)
    return TransitSummary(**defaults)


def _gtfs_context(**overrides) -> TripGtfsServiceContext:
    defaults = dict(
        agency_source="DART",
        route_short_name="057",
        route_long_name="Test Line",
        route_id="R1",
        average_headway_minutes=10.0,
        frequency_classification="frequent",
        service_span_hours=18.0,
        explanation="",
        matched=True,
        unmatched_reason=None,
    )
    defaults.update(overrides)
    return TripGtfsServiceContext(**defaults)


def test_no_bottleneck_triggers_falls_back_to_competitive():
    transit = _transit()  # 25min, low walk, no transfers, no wait

    findings = classify_bottlenecks(transit, DRIVING, transit_penalty=1.25, gtfs_service_context=[])

    assert [f.category for f in findings] == ["competitive"]


def test_high_walking_share_triggers_access_burden():
    transit = _transit(duration_minutes=40, walking_minutes=18, riding_minutes=22)

    findings = classify_bottlenecks(transit, DRIVING, transit_penalty=2.0, gtfs_service_context=[])

    assert "access_burden" in [f.category for f in findings]


def test_high_walking_minutes_but_low_share_does_not_trigger_access_burden():
    # 15 walking minutes alone hits the absolute floor, but on a 90-minute
    # trip that's only 17% -- below the share threshold, so this should not
    # be flagged as an access burden.
    transit = _transit(duration_minutes=90, walking_minutes=15, riding_minutes=75)

    findings = classify_bottlenecks(transit, DRIVING, transit_penalty=4.5, gtfs_service_context=[])

    assert "access_burden" not in [f.category for f in findings]


def test_infrequent_matched_line_triggers_service_frequency():
    transit = _transit()
    context = _gtfs_context(frequency_classification="infrequent", average_headway_minutes=45.0)

    findings = classify_bottlenecks(transit, DRIVING, transit_penalty=1.25, gtfs_service_context=[context])

    frequency_finding = next(f for f in findings if f.category == "service_frequency")
    assert "45" in frequency_finding.evidence
    assert frequency_finding.confidence == "high"


def test_frequent_matched_line_does_not_trigger_service_frequency():
    transit = _transit()
    context = _gtfs_context(frequency_classification="frequent", average_headway_minutes=8.0)

    findings = classify_bottlenecks(transit, DRIVING, transit_penalty=1.25, gtfs_service_context=[context])

    assert "service_frequency" not in [f.category for f in findings]


def test_worst_matched_gtfs_context_picks_least_frequent_line():
    good = _gtfs_context(route_id="GOOD", frequency_classification="frequent")
    bad = _gtfs_context(route_id="BAD", frequency_classification="infrequent")
    unmatched = _gtfs_context(route_id="UNMATCHED", matched=False, frequency_classification=None)

    worst = worst_matched_gtfs_context([good, bad, unmatched])

    assert worst.route_id == "BAD"


def test_worst_matched_gtfs_context_none_when_nothing_matched():
    unmatched = _gtfs_context(matched=False, frequency_classification=None)

    assert worst_matched_gtfs_context([unmatched]) is None


def test_multiple_transfers_triggers_transfer_burden():
    transit = _transit(transfers=2)

    findings = classify_bottlenecks(transit, DRIVING, transit_penalty=1.5, gtfs_service_context=[])

    assert "transfer_burden" in [f.category for f in findings]


def test_single_transfer_does_not_trigger_transfer_burden():
    transit = _transit(transfers=1)

    findings = classify_bottlenecks(transit, DRIVING, transit_penalty=1.5, gtfs_service_context=[])

    assert "transfer_burden" not in [f.category for f in findings]


def test_high_wait_per_transfer_triggers_transfer_coordination():
    transit = _transit(transfers=1, wait_minutes=10)

    findings = classify_bottlenecks(transit, DRIVING, transit_penalty=1.5, gtfs_service_context=[])

    assert "transfer_coordination" in [f.category for f in findings]


def test_low_wait_per_transfer_does_not_trigger_transfer_coordination():
    transit = _transit(transfers=1, wait_minutes=3)

    findings = classify_bottlenecks(transit, DRIVING, transit_penalty=1.5, gtfs_service_context=[])

    assert "transfer_coordination" not in [f.category for f in findings]


def test_unknown_wait_minutes_does_not_trigger_transfer_coordination():
    # wait_minutes is None (a real timestamp was missing) -- must not guess.
    transit = _transit(transfers=2, wait_minutes=None)

    findings = classify_bottlenecks(transit, DRIVING, transit_penalty=1.5, gtfs_service_context=[])

    assert "transfer_coordination" not in [f.category for f in findings]


def test_long_transit_with_low_walking_and_good_frequency_triggers_route_directness():
    transit = _transit(duration_minutes=40, walking_minutes=2, riding_minutes=38)
    context = _gtfs_context(frequency_classification="frequent")

    findings = classify_bottlenecks(transit, DRIVING, transit_penalty=2.0, gtfs_service_context=[context])

    assert "route_directness" in [f.category for f in findings]


def test_route_directness_suppressed_when_frequency_is_the_real_cause():
    # Same slow trip, but the actual matched line is infrequent -- frequency
    # already explains it, so this shouldn't also blame route geometry.
    transit = _transit(duration_minutes=40, walking_minutes=2, riding_minutes=38)
    context = _gtfs_context(frequency_classification="infrequent")

    findings = classify_bottlenecks(transit, DRIVING, transit_penalty=2.0, gtfs_service_context=[context])

    assert "route_directness" not in [f.category for f in findings]


def test_recommend_improvements_maps_one_suggestion_per_bottleneck():
    transit = _transit(walking_minutes=18, duration_minutes=40, riding_minutes=22, transfers=2)
    findings = classify_bottlenecks(transit, DRIVING, transit_penalty=2.0, gtfs_service_context=[])

    suggestions = recommend_improvements(findings)

    assert len(suggestions) == len(findings)
    assert {s.category for s in suggestions} == {f.category for f in findings}
    assert all(s.estimated_impact is None for s in suggestions)
    assert all(s.limitation for s in suggestions)


def test_recommend_improvements_empty_for_competitive_trip():
    findings = classify_bottlenecks(_transit(), DRIVING, transit_penalty=1.1, gtfs_service_context=[])

    assert [f.category for f in findings] == ["competitive"]
    assert recommend_improvements(findings) == []
