# GTFS Service-Quality Metrics (Design Only — Not Implemented)

Defines the metrics for the next milestone: turning raw GTFS schedule data into something that explains *why* a route is usable or car-dependent. Nothing here is built yet — this settles definitions before implementation, same as `docs/caching-plan.md` and `docs/gtfs-integration-plan.md` did before their milestones.

**Standing caveat:** every metric below uses each trip's `stop_sequence = 1` departure time (the route's origin point), not a rider's actual stop. That's the existing "keep it simple" decision already in `gtfs_metrics.py` — worth stating once here instead of per metric.

## 1. Average headway
- **Definition:** Average gap between consecutive departures across the full active service day.
- **Calculation:** Already implemented (`gtfs_metrics._average_gap()`).
- **Rider experience:** "If I show up at a random time, how long until service comes?"
- **Pitfall:** Blends all times of day, so a route frequent at peak but sparse at night just looks "medium" — that's why the window-specific metrics below exist.
- **Raw/label/score:** Raw data. Also the basis for the frequency label (item 8).

## 2. Peak headway
- **Definition:** Average headway within 07:00–09:00 and 16:00–18:00, computed within each window separately (never bridging the gap between them).
- **Calculation:** Already implemented (`_headway_within_windows`, `PEAK_WINDOWS_MINUTES`).
- **Rider experience:** Wait time for a typical work commute.
- **Pitfall:** Pooling AM and PM can hide asymmetry (good morning, bad evening); `null` means "too few trips to estimate," not "no service."
- **Raw/label/score:** Raw data.

## 3. Midday headway
- **Definition:** Average headway within 09:00–15:00.
- **Calculation:** Already implemented (`MIDDAY_WINDOWS_MINUTES`).
- **Rider experience:** Whether the route works for off-peak errands or appointments.
- **Pitfall:** A 6-hour-wide window dilutes a single bad gap more than the narrower peak windows would.
- **Raw/label/score:** Raw data.

## 4. Evening headway
- **Definition:** Average headway within 18:00–22:00.
- **Calculation:** Already implemented (`EVENING_WINDOWS_MINUTES`).
- **Rider experience:** Whether service is reliable after work/dinner.
- **Pitfall:** Covers only 18:00–22:00 — a route with zero late-night service after 22:00 won't show that anywhere except `last_departure_time`.
- **Raw/label/score:** Raw data.

## 5. Number of scheduled trips (trip count)
- **Definition:** Count of active-service trips for the route and date.
- **Calculation:** Already implemented — length of the filtered departure list.
- **Rider experience:** Blunt volume signal; says nothing about distribution alone.
- **Pitfall:** This is the number that silently broke before the date-aware fix (2,202 vs. corrected 457) — sensitive to service_id resolution being correct. Pair with service span (item 7) rather than reading alone.
- **Raw/label/score:** Raw data.

## 6. First / last departure
- **Definition:** Earliest and latest active departure time, in GTFS format (past-`24:00:00` preserved).
- **Calculation:** Already implemented.
- **Rider experience:** "Can I catch this at 5am? Is it still running at 11pm?"
- **Pitfall:** Must stay in raw GTFS format — reformatting `25:30:00` to `01:30:00` would make a route's last trip look like its first.
- **Raw/label/score:** Raw data (timestamp string).

## 7. Total service span
- **Definition:** Hours from first to last departure.
- **Calculation (new, trivial):** `(last_minutes - first_minutes) / 60`, reusing values already computed for item 6. `0` for exactly one trip, `null` only for zero trips — unlike headway's "`null` under 2 points" rule, since span measures a range (well-defined for one point), not a gap (needs two).
- **Rider experience:** "How many hours a day can I actually use this route?" — independent of how frequent it is within that window.
- **Pitfall:** Says nothing about consistency within the span; read alongside headway, not alone.
- **Raw/label/score:** Raw data (hours).

## 8. Service frequency classification
- **Definition:** A label — `"frequent"`, `"moderate"`, `"infrequent"`, or `"minimal"` — derived from average headway (item 1) alone, not a blend of metrics.
- **Thresholds** (a cited convention, not invented): `<=15 min` frequent, `15–30 min` moderate, `>30 min` infrequent, `0 trips` minimal (kept distinct from infrequent — no service is a different situation from rare service). Matches the common "frequent network" definition many US transit agencies use.
- **Rider experience:** Quick plain-language answer to "can I just show up, or do I need to plan around a schedule?"
- **Pitfall:** The 15/30 cutoff is a judgment call, not a discovered fact — document it as an adopted convention, same as `scoring.py`'s heuristic constants.
- **Raw/label/score:** This is the label itself — single-metric, not a composite.

## Should there be a composite "service_quality_score"?

**Not yet.**
1. **Unit mismatch** — minutes, hours, and counts can't combine into one 0–100 number without arbitrary calibration.
2. **Unjustified weighting** — no evidence exists for "headway matters 2x more than span."
3. **Works against the goal** — the target output is a factor list ("24-min wait, low frequency, 2 transfers"), which raw metrics + one label already provide; a score would need to be decomposed back into factors to explain itself anyway.
4. **No consumer needs it yet** — a score earns its complexity when something needs to *rank* routes. Nothing here does yet.

Ship the raw metrics and the one classification. Revisit a score only when a real ranking use case can justify specific weights.

## Proposed next-endpoint shape (not implemented)

```json
{
  "agency_source": "CTA",
  "route_id": "79",
  "service_date": "2026-08-11",
  "average_headway_minutes": 3.1,
  "peak_headway_minutes": 2.1,
  "midday_headway_minutes": 3.2,
  "evening_headway_minutes": 3.1,
  "trip_count": 457,
  "first_departure_time": "00:03:00",
  "last_departure_time": "23:55:00",
  "service_span_hours": 23.9,
  "frequency_class": "frequent"
}
```

Everything except `service_span_hours` and `frequency_class` is already computed by the existing `/service-summary` endpoint — those two are the only new calculations this milestone adds.

## Out of scope for this milestone

Stop access/walking burden, transfer burden, connecting to `trip_scenarios`/route comparison (step 5 of the six-step plan), frontend display, and the composite score.
