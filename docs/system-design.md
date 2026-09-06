# System Design

High-level component interactions. Deeper detail per subsystem lives in its own doc — see `docs/architecture.md` for backend layering, `docs/gtfs-integration-plan.md` for static GTFS ingestion, and `docs/google-routes-integration.md` for the arbitrary-trip flow below.

## Two comparison paths, one response shape family

```text
Curated (fallback/demo):
React → FastAPI → trip_scenarios (SQLite) → scoring.py/simulator.py → RouteComparison

Arbitrary trip (primary):
React → FastAPI → Google Routes API (DRIVE + TRANSIT)
                       ↓
                 GTFS enrichment (match transit lines → gtfs_routes → gtfs_metrics.py)
                       ↓
                 TripCompareResponse → React
```

Both paths report through the same FastAPI app and the same GTFS-derived service-quality logic (`gtfs_metrics.py`), but produce different response schemas (`RouteComparison` vs `TripCompareResponse`) — the curated flow's fields (fare, emissions, city) don't exist for an arbitrary trip, so the two are never forced into one shape.

## Where GTFS fits

GTFS (`gtfs_*` tables, imported from CTA/DART static feeds) is a supporting data source in both paths — it supplies scheduled-service quality (headway, frequency, span) and route-line geometry, but never originates a trip itinerary. Arbitrary-trip routing and turn-by-turn geometry come from Google Routes; GTFS explains *why* the scheduled service behaves the way it does once a line is identified.
