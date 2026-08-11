# Caching Plan (Design Only — Not Implemented)

This document describes how Transit Improvement Lab should cache route lookups once it starts calling external routing/transit APIs. **Nothing in this document is built yet.** As of this writing, the app has no external API calls at all — every route comes from `data/sample-routes.json`, seeded into SQLite. This is a plan to read before that work starts, not a description of current behavior.

## 1. Why Caching Matters

Once the app calls a real external source — Google Maps, OpenRouteService, or a DART/CTA GTFS feed — every route lookup becomes:

- **Slower.** An external HTTP call takes far longer than a local SQLite read.
- **Costly or rate-limited.** Most routing APIs charge per request or cap how many requests you can make per day.
- **Repetitive.** The same handful of popular origin/destination pairs (e.g. "Hyde Park → The Loop") will likely get searched over and over. There's no reason to pay for and wait on the same answer twice.

Caching means: the first time someone looks up a route, call the external API and save the result. Every lookup after that, for the same origin/destination/mode, reads the saved result instead of calling the API again.

## 2. Current Architecture

Today, the whole app is external-API-free:

```text
React + TypeScript frontend (Vite)
        ↓  fetch()
FastAPI backend
        ↓
SQLite database (trip_scenarios table)
        ↓
Python scoring and simulation services
```

`route_repository.py` reads pre-seeded, manually estimated route data. `dashboard_repository.py` runs aggregate SQL over that same data. There is no HTTP call to anything outside this machine. This is intentional — see the root README's "Data & Accuracy" section — and it means there is currently nothing to cache.

## 3. Future Cache-First Architecture

When a real external source is added, the lookup flow should gain a cache layer *in front of* the external call, not instead of the existing `trip_scenarios` data:

```text
React + TypeScript frontend
        ↓  fetch()
FastAPI backend
        ↓
Cache check (route_lookup_cache table in SQLite)
        ↓ cache miss
External API / GTFS feed (Google Maps, OpenRouteService, DART, CTA, ...)
        ↓
Normalize response into our own route-metric shape
        ↓
Save to route_lookup_cache
        ↓
Return normalized metrics to frontend
```

`trip_scenarios` (today's manual sample data) and `route_lookup_cache` (future external lookups) are separate tables with separate purposes. One holds hand-entered example routes for demoing the app; the other holds real answers from real APIs, kept only long enough to avoid re-paying for them.

## 4. Proposed Table: `route_lookup_cache`

```sql
CREATE TABLE IF NOT EXISTS route_lookup_cache (
  id INTEGER PRIMARY KEY,
  origin_text TEXT NOT NULL,
  destination_text TEXT NOT NULL,
  city TEXT NOT NULL,
  mode TEXT NOT NULL,
  external_source TEXT NOT NULL,
  raw_external_response_json TEXT NOT NULL,
  normalized_route_metrics_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL
);
```

A `UNIQUE(origin_text, destination_text, city, mode, external_source)` constraint is worth adding once this is built — it stops the same lookup from being cached twice under two different rows.

## 5. Field Notes

| Field | Purpose |
|---|---|
| `id` | Row identifier, same pattern as `trip_scenarios.id`. |
| `origin_text` / `destination_text` | The raw text the user searched for (e.g. "Bishop Arts"), not a route category — external APIs geocode free text, so the cache key needs to match what was actually searched. |
| `city` | Lets cached rows be filtered/cleared per city, matching how the rest of the app already scopes by city. |
| `mode` | `"driving"` or `"transit"` — a single origin/destination pair needs separate cache rows per travel mode, since they hit different parts of an external API (or different APIs entirely). |
| `external_source` | Which API answered (e.g. `"google_maps"`, `"cta_gtfs"`, `"dart_gtfs"`). Lets different sources be cached, invalidated, or rate-limit-tracked independently. |
| `raw_external_response_json` | The unmodified response body, stored as JSON text. If a bug is later found in how we normalize responses, this lets us re-normalize from what we already have instead of re-calling (and re-paying for) the API. |
| `normalized_route_metrics_json` | The response translated into our own shape — ideally something close to the existing `RouteScenario`/`RouteComparison` fields, so the rest of the app doesn't need to know or care where a route came from. This is what day-to-day reads actually use. |
| `created_at` | When this row was written. SQLite has no native datetime type, so this is stored as an ISO 8601 string (e.g. `"2026-08-04T09:00:00Z"`). |
| `expires_at` | When this row should stop being treated as valid. Same string format as `created_at`. |

## 6. Cache Flow

1. Frontend sends an origin, destination, city, and mode to the backend (a new lookup endpoint, separate from the existing `/api/routes` endpoints).
2. Backend checks `route_lookup_cache` for a row matching that origin/destination/city/mode/source.
3. **Cache hit, not expired** (`expires_at` is still in the future): return the stored `normalized_route_metrics_json` immediately. No external call happens.
4. **Cache miss, or the row is expired:** call the external API or feed.
5. Normalize the raw response into our internal route-metric shape.
6. Save both the raw and normalized response into `route_lookup_cache`, replacing any expired row for that same lookup.
7. Return the normalized metrics to the frontend — same shape whether it came from cache or a fresh API call, so the frontend never needs to know which happened.

## 7. Cache Invalidation Strategy

- **TTL per source, not one global constant.** Different data goes stale at different speeds: a geocoded origin/destination pair barely changes, so it could be cached for weeks. A driving-time estimate might be cached for hours. Live transit predictions (if ever added) should not be cached longer than a few minutes, if at all.
- **Check expiration on read, not on a timer.** When a lookup comes in, compare `expires_at` to the current time. An expired row is just treated as a cache miss — no background job is required to make this correct. A periodic cleanup script to delete old expired rows is a nice-to-have, not a requirement, and should come later.
- **Normalization changes invalidate everything.** If the shape of `normalized_route_metrics_json` ever changes (a new field is added, a calculation changes), old cached rows won't match. The simplest fix at that point is to clear the whole cache table, the same way `seed_db.py` already fully replaces `trip_scenarios` rather than trying to patch them in place.

## 8. What Not to Cache Yet

- **The existing manual sample data.** `trip_scenarios` is already a local, instant SQLite read. Caching it would add a layer of complexity for zero benefit.
- **Anything before an external API actually exists.** There is nothing to cache until a real external source is wired in — this document is preparation, not a reason to build the table early.
- **Live or real-time data**, if that's ever added (live bus positions, live delay predictions). Caching data that's supposed to be "live" for more than a few seconds would show users wrong information, which defeats the point of it being live.
- **Failed responses.** A timeout, rate-limit error, or malformed response from an external API should never be saved as if it were a valid cached answer.
- **Anything tied to a specific person**, if user accounts are ever added. This cache should stay scoped to origin/destination/mode/source — a shared lookup, not a personal record — to avoid storing unnecessary personal data.

## 9. V2 Implementation Checklist

When this is actually ready to build, in order:

1. Pick **one** external source to integrate first (e.g. Google Maps Directions API, or one city's GTFS feed) — not all of DART/CTA/GTFS/Google Maps at once.
2. Add the `route_lookup_cache` table to `database.py`, following the same `CREATE TABLE IF NOT EXISTS` pattern already used for `trip_scenarios`.
3. Add `cache_repository.py` under `app/repositories/`, with functions like `get_cached_lookup(...)` and `save_lookup(...)` — mirroring how `route_repository.py` and `dashboard_repository.py` are already structured.
4. Write a normalization function that converts that one external source's raw response into the internal route-metric shape, so the rest of the app stays source-agnostic.
5. Add a new lookup endpoint that wires together: check cache → call external API on miss → normalize → save → return.
6. Set a TTL per source/data type (not one constant for everything), per the invalidation strategy above.
7. Add pytest tests for the cache repository — cache hit, cache miss, and an expired row correctly treated as a miss — using the same temporary-database pattern already used in `test_route_repository.py` and `test_dashboard_repository.py`.
8. Add basic logging or a counter for cache hits vs. misses, so it's possible to confirm caching is actually reducing external calls, not just assumed to be.
9. Only after all of the above is working and stable, consider a periodic cleanup job for expired rows. It's an optimization, not a correctness requirement — expired rows are already ignored on read.
