# Google Routes Integration

This document describes the new arbitrary origin/destination trip-comparison path, built on top of the Google Routes API. It supersedes the "pick one external source first" step from `docs/caching-plan.md`'s V2 checklist — Google Routes is that one source.

## 1. Why This Exists

The curated `trip_scenarios` flow (`GET /api/routes`, `GET /api/routes/{id}/comparison`) only knows about a fixed set of hand-picked origin/destination pairs. It cannot answer "how does *my* trip compare?" for an address someone actually types in. This milestone adds that real path, without removing the curated one — the curated flow stays as a fallback/demo dataset until the new path is verified stable.

## 2. Flow

```text
USER
  │  origin + destination
  ▼
REACT
  │  POST /api/trips/compare
  ▼
FASTAPI
  │
  ├── Google Routes API — DRIVE  → driving duration, distance, polyline
  │
  ├── Google Routes API — TRANSIT → itinerary: transit legs/steps, walking, route/line names
  │
  └── GTFS enrichment
        │  for each Google transit line:
        │  match agency + route name → imported gtfs_routes
        │  (only if unambiguous — never guessed)
        │       │
        │       ▼
        │  existing date-aware service logic:
        │  headway, frequency, service span, explanation
        │
        ▼
  COMPARISON RESPONSE
        │
        ▼
      REACT
```

Before this milestone, `driving`/`transit` never existed as backend concepts — every comparison came from manually-entered `trip_scenarios` rows. After this milestone, GTFS is a supporting enrichment source for scheduled-service context, not the thing that produces the itinerary or the map geometry. See `docs/gtfs-integration-plan.md` and the route-geometry work for how GTFS is used elsewhere in the app.

## 3. New Backend Layer: `app/clients/`

`app/architecture.md` didn't previously have a place for outbound calls to a third-party API — `repositories/` is DB-only, `services/` is pure calculation. `app/clients/google_routes_client.py` fills that gap: it calls `POST https://routes.googleapis.com/directions/v2:computeRoutes`, returns parsed JSON, and raises `GoogleRoutesApiError` on failure. It does no normalization and no business logic — see `docs/architecture.md` for the full layering rule.

`app/config.py` loads `GOOGLE_MAPS_API_KEY` from `.env` (via `python-dotenv`) and is the only place that reads it. The key is never sent to the frontend, never logged, and never included in an error message — a failure returns a generic "Could not reach the routing service" (or "...places service") message. The same key is reused for Places Autocomplete (section 10) via `app/clients/google_places_client.py`.

## 4. Request Contract

```
POST /api/trips/compare
{
  "origin": { "label": "Bishop Arts, Dallas, TX" },
  "destination": { "label": "DFW International Airport", "place_id": "ChIJ..." }
}
```

`label` is always the display text; `place_id` (from a selected autocomplete suggestion — section 10) is preferred for the actual Google Routes waypoint when present, since it's unambiguous where free text can geocode to the wrong place. See `app/trip_compare_schemas.LocationInput`.

Backend calls Google Routes twice per request — `travelMode: DRIVE` (routing preference `TRAFFIC_UNAWARE`, for a typical/average comparison, not live traffic) and `travelMode: TRANSIT` with an explicit `departureTime` (section 9) — using a `X-Goog-FieldMask` scoped to only the fields this app actually uses, per Google's billing-by-field-mask model.

## 5. Response Contract

```json
{
  "origin": "...",
  "destination": "...",
  "departure_time": "2026-09-07T09:00:00-05:00",
  "driving": { "duration_minutes": 14, "distance_miles": 4.8, "polyline": "..." },
  "transit": {
    "duration_minutes": 31, "distance_miles": 5.2, "walking_minutes": 6,
    "transfers": 0, "route_names": ["620"], "polyline": "..."
  },
  "gtfs_service_context": [
    {
      "agency_source": "DART", "route_id": "27243",
      "route_short_name": "620", "route_long_name": "DALLAS STREETCAR",
      "average_headway_minutes": 20, "frequency_classification": "moderate",
      "service_span_hours": 18, "explanation": "...",
      "matched": true, "unmatched_reason": null
    }
  ],
  "comparison": { "transit_penalty": 2.21, "extra_minutes": 17, "verdict": "..." }
}
```

`origin`/`destination` in the response echo the request's `label` (for display), regardless of whether `place_id` was used for routing. `departure_time` is included so the frontend can show *when* this hypothetical trip was analyzed for (section 9) — this is a deliberately separate shape from `RouteComparison` (the curated-flow response) — see `app/trip_compare_schemas.py`. Forcing the old schema here would mean inventing `fare_cost`, `gas_cost`, `driving_emissions_kg`, `route_category`, and `city` for a trip that has none of those; the new schema simply doesn't have those fields.

## 6. GTFS Matching Rule

For each transit step Google returns, the backend extracts the agency name, route short/long name, and headsign, then:

1. Maps Google's agency display name to this app's `agency_source` label by looking it up against our own imported `gtfs_agencies.agency_name` (`gtfs_service_repository.get_agency_source_by_name`) — both ultimately come from the same published GTFS `agency.txt`, so this stays correct (e.g. across a casing difference like `"DALLAS AREA RAPID TRANSIT"`) without hardcoding a guessed string, and without a hard-coded mapping to maintain as more agencies are imported.
2. Looks up candidate `gtfs_routes` rows within that agency by `route_short_name` (preferred) or `route_long_name` (fallback).
3. **Exactly one candidate** → matched; reuse the existing date-aware headway/frequency/span logic from `gtfs_metrics.py` (the same functions `GET /api/gtfs/.../service-summary` already uses).
4. **Zero or multiple candidates** → unmatched. The line still appears in `gtfs_service_context` with `matched: false` and a short `unmatched_reason`, never a guessed route. The transit itinerary itself (duration, walking, route names) is unaffected either way.

## 7. Map Geometry

The map for an arbitrary trip renders the **polyline Google Routes returns** (decoded client-side), because that's the actual real path for that specific trip. GTFS shape geometry (see the route-geometry milestone) remains what it already was: route-level context for a specific scheduled service line, shown in the GTFS service card — not used to draw the arbitrary-trip route.

## 8. Caching — Deferred

Per `docs/caching-plan.md` section 9, item 1 ("pick one external source first, not all at once") — this milestone is that pick, but the cache table itself is **not** built yet. `route_lookup_cache` gets added only after this end-to-end flow is confirmed working, following the existing design in `caching-plan.md` unchanged. Every request currently calls Google fresh.

## 9. Departure Time Is Never "Now"

TRANSIT results depend heavily on time of day and day of week — a request made at 2am Sunday would show sparse or nonexistent service that says nothing useful about a rider's real weekday commute. `app/services/trip_comparison.resolve_representative_departure_time()` always returns the next weekday at 9:00 AM `America/Chicago` (both CTA and DART operate in Central time), strictly after the actual current moment — never a fixed calendar date, since Google's TRANSIT mode rejects a `departureTime` in the past and a hardcoded date would eventually become one. This same date anchors both the Google TRANSIT call and the GTFS service-date lookup in section 6, so both halves of the comparison describe the same hypothetical trip. The resolved value is returned as `departure_time` in the response (section 5) so the frontend can show the user what moment was actually analyzed.

## 10. Place Autocomplete

```text
User types "dfw"
        ↓
GET /api/places/autocomplete?input=dfw
        ↓
app/clients/google_places_client.py -- Places API (New) Autocomplete,
biased toward Dallas AND Chicago (two calls, one per metro circle --
locationBias only supports one region per call, and the cities are
~800 miles apart, so a single shared bias would barely prefer either)
        ↓
app/services/place_search.py -- dedupe by place_id, cap at 8
        ↓
user selects "DFW International Airport"
        ↓
{ "label": "DFW International Airport, ...", "place_id": "ChIJ..." }
        ↓
POST /api/trips/compare -- place_id used for the Google Routes waypoint
instead of the ambiguous display text
```

The frontend (`PlaceAutocompleteInput.tsx`) debounces input by 300ms and only queries once the input is at least 3 characters, to keep this affordable per keystroke. Selecting a suggestion is not required — typing a full address and pressing Compare still works via the `label`-only fallback (`{"placeId": ...}` vs. `{"address": ...}` in the Google Routes waypoint; see `google_routes_client._to_waypoint`), the same "honest fallback, no hard requirement" pattern already used for GTFS matching in section 6.

Each `PlaceSuggestion` carries a server-computed `label` (`"primary, secondary"`, or just `primary` when there's no secondary text) so the frontend has one ready-to-use string instead of reassembling it. The input visually distinguishes two states: **confirmed** (a suggestion was selected — green border, checkmark, `place_id` set) and **unconfirmed** (typed text with no matching selection — a small "Unverified — select a suggestion or enter a full address" note, or "Autocomplete unavailable — enter a full address" if the Places call itself is failing). Editing a confirmed field's text immediately drops back to unconfirmed and clears `place_id` — there is no code path that keeps routing on a stale selection after the label has changed. The dropdown supports arrow-key navigation, Enter to select, Escape to close, and click.

## 11. What's Explicitly Out of Scope Here

- Real-time traffic (`TRAFFIC_AWARE`) — driving duration uses `TRAFFIC_UNAWARE` for a stable, typical comparison.
- Multiple route alternatives — one DRIVE result, one TRANSIT result per request.
- Resolving a `place_id` to lat/lng via the Place Details endpoint — Google Routes accepts a `placeId` waypoint directly, so that extra call/cost isn't needed for this flow.
- Removing the curated `trip_scenarios` flow — it stays as a secondary, always-available demo dataset.
