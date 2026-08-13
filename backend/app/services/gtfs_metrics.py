"""
GTFS service-summary calculations: date/calendar resolution, GTFS time
parsing, and headway math.

No SQL and no FastAPI objects here — this takes plain values already
fetched by gtfs_service_repository.py (departure-time strings, calendar
rows, calendar_dates exceptions) and returns plain values or dicts back.
Kept separate from scoring.py / simulator.py since those work over the
app's own trip_scenarios data, not imported GTFS schedules.

Headway = the average time gap between consecutive scheduled departures.
Smaller headway means more frequent service.
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

# Index 0 = Monday ... 6 = Sunday, matching Python's date.weekday().
GTFS_WEEKDAY_COLUMNS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

# Used only if an agency's own gtfs_agencies.agency_timezone is missing or
# unrecognized. Not an arbitrary choice: both agencies this app currently
# imports (CTA in Chicago, DART in Dallas) are Central Time.
DEFAULT_TIMEZONE = "America/Chicago"

# Each window is (start_minute, end_minute), in minutes after midnight.
# "Peak" has two separate ranges (morning and evening rush); midday and
# evening each have one.
PEAK_WINDOWS_MINUTES = [(7 * 60, 9 * 60), (16 * 60, 18 * 60)]  # 07:00-09:00 and 16:00-18:00
MIDDAY_WINDOWS_MINUTES = [(9 * 60, 15 * 60)]  # 09:00-15:00
EVENING_WINDOWS_MINUTES = [(18 * 60, 22 * 60)]  # 18:00-22:00

# Frequency classification thresholds, from docs/service-quality-metrics.md.
# Not derived from this app's own data — this mirrors a widely-used transit
# industry convention (many US agencies define a "frequent network" as
# headways of 15 minutes or better all day). Document changes to these in
# that file, not just here.
FREQUENT_HEADWAY_MAX_MINUTES = 15
MODERATE_HEADWAY_MAX_MINUTES = 30

# Used only by explain_service_quality() below. Not documented elsewhere
# yet -- this app's own working assumption, not an external standard:
# routes running less than half a day are meaningfully more restricted
# than routes spanning a typical 5am-1am urban service day.
SHORT_SERVICE_SPAN_HOURS = 12


def resolve_service_date(requested_date: date | None, agency_timezone: str | None) -> date:
    """
    Returns requested_date if one was given. Otherwise returns "today" in
    the agency's own timezone, falling back to DEFAULT_TIMEZONE if the
    agency has no timezone on file or it isn't a recognized zone name.
    """
    if requested_date is not None:
        return requested_date

    timezone_name = agency_timezone or DEFAULT_TIMEZONE
    try:
        zone = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        zone = ZoneInfo(DEFAULT_TIMEZONE)

    return datetime.now(zone).date()


def compute_active_service_ids(
    calendar_service_ids: list[str],
    calendar_date_exceptions: list[tuple[str, str]],
) -> list[str]:
    """
    Combines gtfs_calendar's weekday-matched service_ids with
    gtfs_calendar_dates exceptions for one exact date:

        active = calendar service_ids + additions (type "1") - removals (type "2")

    calendar_date_exceptions is a list of (service_id, exception_type)
    pairs, exactly as returned by
    gtfs_service_repository.get_calendar_date_exceptions().
    """
    active = set(calendar_service_ids)

    for service_id, exception_type in calendar_date_exceptions:
        if exception_type == "1":
            active.add(service_id)
        elif exception_type == "2":
            active.discard(service_id)

    return sorted(active)


def parse_gtfs_time_to_minutes(time_str: str) -> int:
    """
    Converts a GTFS "HH:MM:SS" time into minutes after midnight.

    GTFS deliberately allows hours past 24 (e.g. "25:30:00") to represent
    service after midnight that's still logically part of the previous
    service day, so this does not wrap the value back into 0-23 — 1:30am
    the next calendar day stays 1530 minutes, not 90.
    """
    hours, minutes, seconds = (int(part) for part in time_str.split(":"))
    return hours * 60 + minutes + seconds // 60


def _format_minutes_as_gtfs_time(total_minutes: int) -> str:
    hours, minutes = divmod(total_minutes, 60)
    return f"{hours:02d}:{minutes:02d}:00"


def _average_gap(sorted_minutes: list[int]) -> float | None:
    """Average gap between consecutive values. None if fewer than 2 values."""
    if len(sorted_minutes) < 2:
        return None

    gaps = [later - earlier for earlier, later in zip(sorted_minutes, sorted_minutes[1:])]
    return round(sum(gaps) / len(gaps), 1)


def _headway_within_windows(sorted_minutes: list[int], windows: list[tuple[int, int]]) -> float | None:
    """
    Average headway using only gaps between departures that fall inside
    the same window.

    Gaps are never computed across two different windows — e.g. between
    the last morning-peak departure and the first evening-peak departure.
    That multi-hour gap reflects the midday lull in service, not how
    frequently "peak" service actually runs, so it would badly skew the
    average if it were included.
    """
    all_gaps: list[int] = []

    for start, end in windows:
        minutes_in_window = [minute for minute in sorted_minutes if start <= minute < end]
        all_gaps.extend(
            later - earlier for earlier, later in zip(minutes_in_window, minutes_in_window[1:])
        )

    if not all_gaps:
        return None

    return round(sum(all_gaps) / len(all_gaps), 1)


def _service_span_hours(sorted_minutes: list[int]) -> float | None:
    """
    Hours from first to last departure. 0.0 for exactly one departure
    (first equals last); None only when there are zero departures.

    This differs from _average_gap's "None if fewer than 2 values" rule on
    purpose: span measures a range, which is well-defined even for a
    single point, while headway measures a gap between two points, which
    requires two points to exist at all.
    """
    if not sorted_minutes:
        return None

    return round((sorted_minutes[-1] - sorted_minutes[0]) / 60, 1)


def _classify_frequency(average_headway_minutes: float | None) -> str:
    """
    Labels average headway per the thresholds in
    docs/service-quality-metrics.md. A None average (fewer than 2
    departures to measure a gap from) is "minimal", kept distinct from
    "infrequent" — no measurable service is a different situation from
    service that just runs rarely.
    """
    if average_headway_minutes is None:
        return "minimal"
    if average_headway_minutes <= FREQUENT_HEADWAY_MAX_MINUTES:
        return "frequent"
    if average_headway_minutes <= MODERATE_HEADWAY_MAX_MINUTES:
        return "moderate"
    return "infrequent"


def calculate_service_summary(departure_time_strings: list[str]) -> dict:
    """
    Computes trip_count, first/last departure, headway figures, service
    span, and a frequency label from a list of raw GTFS departure-time
    strings. Doesn't know about routes, agencies, or calendar dates —
    those are the caller's job to attach.
    """
    departure_minutes = sorted(parse_gtfs_time_to_minutes(time_str) for time_str in departure_time_strings)

    first_departure_time = _format_minutes_as_gtfs_time(departure_minutes[0]) if departure_minutes else None
    last_departure_time = _format_minutes_as_gtfs_time(departure_minutes[-1]) if departure_minutes else None
    average_headway_minutes = _average_gap(departure_minutes)

    return {
        "trip_count": len(departure_minutes),
        "first_departure_time": first_departure_time,
        "last_departure_time": last_departure_time,
        "average_headway_minutes": average_headway_minutes,
        "peak_headway_minutes": _headway_within_windows(departure_minutes, PEAK_WINDOWS_MINUTES),
        "midday_headway_minutes": _headway_within_windows(departure_minutes, MIDDAY_WINDOWS_MINUTES),
        "evening_headway_minutes": _headway_within_windows(departure_minutes, EVENING_WINDOWS_MINUTES),
        "service_span_hours": _service_span_hours(departure_minutes),
        "frequency_classification": _classify_frequency(average_headway_minutes),
    }


def explain_service_quality(frequency_classification: str, service_span_hours: float | None) -> str:
    """
    Builds a short, rule-based explanation from already-computed GTFS
    metrics only -- no new calculation, no composite score. Used for
    GtfsServiceContext (see route_scenarios.py's comparison endpoint), not
    the plain /service-summary endpoint.

    Frequency drives the primary observation; a notably short service
    span (see SHORT_SERVICE_SPAN_HOURS) adds a second one. Rules are
    intentionally simple and spelled out here rather than hidden behind a
    score, per docs/service-quality-metrics.md's recommendation against
    inventing a composite score.
    """
    if frequency_classification == "infrequent":
        observations = ["Low scheduled frequency may contribute to waiting time."]
    elif frequency_classification == "moderate":
        observations = ["Moderate scheduled frequency; some waiting time is likely but not severe."]
    elif frequency_classification == "minimal":
        observations = ["No reliable scheduled service was found for this date."]
    else:  # "frequent"
        observations = [
            "Scheduled frequency is relatively strong; delay likely comes from transfers, "
            "walking, or route geometry instead."
        ]

    if service_span_hours is not None and service_span_hours < SHORT_SERVICE_SPAN_HOURS:
        observations.append("Limited service span may reduce flexibility outside typical hours.")

    return " ".join(observations)
