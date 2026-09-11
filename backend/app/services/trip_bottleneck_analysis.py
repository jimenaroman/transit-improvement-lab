"""
V1 heuristic bottleneck classifier for a single Google-routed trip.

Given only fields already computed elsewhere (walking/riding/wait minutes
from the real itinerary, transfers, the transit penalty, and any matched
GTFS frequency data), flags which structural categories plausibly
contribute to why transit is slower than driving for this one trip. This
never claims causation -- only that a measured pattern is consistent with
a named category, same spirit as simulator.py's RouteScenario heuristic.
Thresholds below are initial assumptions, not validated engineering
figures, and several intentionally match simulator.py's for consistency
across the product.

recommend_improvements() maps each bottleneck to one structured suggestion.
estimated_impact is always None here: simulator.py's before/after estimates
only apply to curated RouteScenario rows, and there's no equivalent
validated model for an arbitrary Google-routed trip yet -- inventing a
number for this data path would be a guess, not an estimate.
"""

from app.trip_compare_schemas import (
    DrivingSummary,
    TransitSummary,
    TripBottleneck,
    TripGtfsServiceContext,
    TripImprovementSuggestion,
)

WALKING_BURDEN_MINUTES = 15
WALKING_BURDEN_SHARE = 0.25

TRANSFER_BURDEN_TRIGGER = 2

COORDINATION_WAIT_PER_TRANSFER_MINUTES = 8

INDIRECT_ROUTE_MULTIPLIER = 1.8
LOW_WALKING_MINUTES_FOR_ROUTE_CHECK = 10

# Worst-to-best, matching gtfs_metrics.py's _classify_frequency() labels.
FREQUENCY_SEVERITY = ["minimal", "infrequent", "moderate", "frequent"]
POOR_FREQUENCY_CLASSIFICATIONS = {"infrequent", "moderate"}


def worst_matched_gtfs_context(gtfs_service_context: list[TripGtfsServiceContext]) -> TripGtfsServiceContext | None:
    """The matched line with the least frequent service, or None if nothing matched."""
    matched = [context for context in gtfs_service_context if context.matched]
    if not matched:
        return None
    return min(matched, key=lambda context: FREQUENCY_SEVERITY.index(context.frequency_classification or "frequent"))


def classify_bottlenecks_from_metrics(
    *,
    walking_minutes: int,
    wait_minutes: int | None,
    transit_minutes: int,
    driving_minutes: int,
    transfers: int,
    transit_penalty: float,
    frequency_classification: str | None,
    average_headway_minutes: float | None,
) -> list[TripBottleneck]:
    """
    The reusable core: plain scalar metrics in, findings out. Takes plain
    values rather than TransitSummary/DrivingSummary so the same rules can
    classify both a live Google-routed trip and a curated RouteScenario
    row, which have different shapes for the same underlying concepts.
    """
    findings: list[TripBottleneck] = []

    walking_share = walking_minutes / transit_minutes if transit_minutes else 0
    if walking_minutes >= WALKING_BURDEN_MINUTES and walking_share >= WALKING_BURDEN_SHARE:
        findings.append(
            TripBottleneck(
                category="access_burden",
                label="High walking/access burden",
                evidence=(
                    f"Walking makes up {walking_minutes} of {transit_minutes} minutes "
                    f"({round(walking_share * 100)}% of the trip)."
                ),
                confidence="moderate",
            )
        )

    if frequency_classification in POOR_FREQUENCY_CLASSIFICATIONS:
        headway_text = f"about {average_headway_minutes:.0f} minutes" if average_headway_minutes is not None else "irregular"
        findings.append(
            TripBottleneck(
                category="service_frequency",
                label="Poor service frequency",
                evidence=(
                    f"The least frequent scheduled line on this trip runs every {headway_text} on average "
                    f"({frequency_classification})."
                ),
                confidence="high",
            )
        )

    if transfers >= TRANSFER_BURDEN_TRIGGER:
        findings.append(
            TripBottleneck(
                category="transfer_burden",
                label="Multiple transfers",
                evidence=f"This trip requires {transfers} transfers.",
                confidence="high",
            )
        )

    if wait_minutes is not None and transfers >= 1:
        wait_per_transfer = wait_minutes / transfers
        if wait_per_transfer >= COORDINATION_WAIT_PER_TRANSFER_MINUTES:
            findings.append(
                TripBottleneck(
                    category="transfer_coordination",
                    label="Poor transfer coordination",
                    evidence=(
                        f"Waiting averages {wait_per_transfer:.0f} minutes per transfer "
                        f"({wait_minutes} total minutes across {transfers} transfer(s))."
                    ),
                    confidence="moderate",
                )
            )

    if (
        driving_minutes > 0
        and transit_minutes >= driving_minutes * INDIRECT_ROUTE_MULTIPLIER
        and walking_minutes < LOW_WALKING_MINUTES_FOR_ROUTE_CHECK
        and frequency_classification != "infrequent"
    ):
        findings.append(
            TripBottleneck(
                category="route_directness",
                label="Indirect route / high in-vehicle time",
                evidence=(
                    f"Transit takes {transit_minutes} minutes versus {driving_minutes} minutes "
                    "driving, with low walking time and no severe frequency issue -- most of the extra time is "
                    "spent riding."
                ),
                confidence="low",
            )
        )

    if not findings:
        findings.append(
            TripBottleneck(
                category="competitive",
                label="Generally competitive trip",
                evidence=f"No dominant bottleneck was identified; transit takes {transit_penalty}x as long as driving.",
                confidence="moderate",
            )
        )

    return findings


def classify_bottlenecks(
    transit: TransitSummary,
    driving: DrivingSummary,
    transit_penalty: float,
    gtfs_service_context: list[TripGtfsServiceContext],
) -> list[TripBottleneck]:
    """Live-trip convenience wrapper: unpacks TransitSummary/DrivingSummary into classify_bottlenecks_from_metrics()."""
    worst_context = worst_matched_gtfs_context(gtfs_service_context)

    return classify_bottlenecks_from_metrics(
        walking_minutes=transit.walking_minutes,
        wait_minutes=transit.wait_minutes,
        transit_minutes=transit.duration_minutes,
        driving_minutes=driving.duration_minutes,
        transfers=transit.transfers,
        transit_penalty=transit_penalty,
        frequency_classification=worst_context.frequency_classification if worst_context else None,
        average_headway_minutes=worst_context.average_headway_minutes if worst_context else None,
    )


_RECOMMENDATION_TEMPLATES = {
    "access_burden": (
        "Improve stop access and pedestrian connections",
        "Shortening the walk to or from transit reduces this trip's biggest measured burden directly.",
    ),
    "service_frequency": (
        "Increase service frequency",
        "Shorter headways reduce the average wait for any rider, independent of how this specific trip happened to line up with the schedule.",
    ),
    "transfer_burden": (
        "Reduce transfers via through-routing",
        "Fewer required transfers reduces total trip complexity and the risk of a missed connection.",
    ),
    "transfer_coordination": (
        "Coordinate transfer schedules (timed transfers)",
        "Aligning arrival and departure times at the transfer point reduces platform waiting without changing frequency.",
    ),
    "route_directness": (
        "Provide more direct or limited-stop service",
        "Reducing detour and intermediate stops cuts in-vehicle time directly.",
    ),
}

_LIMITATION = "Based on this single simulated trip only -- not validated against real ridership, engineering studies, or cost."


def recommend_improvements(bottlenecks: list[TripBottleneck]) -> list[TripImprovementSuggestion]:
    """One suggestion per non-"competitive" bottleneck -- a competitive trip has nothing to recommend against."""
    suggestions = []

    for bottleneck in bottlenecks:
        template = _RECOMMENDATION_TEMPLATES.get(bottleneck.category)
        if template is None:
            continue
        title, rationale = template
        suggestions.append(
            TripImprovementSuggestion(
                category=bottleneck.category,
                title=title,
                evidence=bottleneck.evidence,
                rationale=rationale,
                estimated_impact=None,
                confidence=bottleneck.confidence,
                limitation=_LIMITATION,
            )
        )

    return suggestions
