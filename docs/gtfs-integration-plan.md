# GTFS Integration Plan (Design Only — Not Implemented)

This document plans how Transit Improvement Lab should ingest real transit schedule data from DART and CTA using GTFS, starting with the static schedule feed and only later considering real-time data. **Nothing in this document is built yet.** As of this writing, all route data comes from `data/sample-routes.json` — 12 manually estimated routes, seeded into the `trip_scenarios` SQLite table. This plan describes the next data source, not current behavior. See also [docs/caching-plan.md](caching-plan.md), which this plan builds on for anything that involves a live external call.

## 1. Why Static GTFS Should Come Before Real-Time APIs

- **Real-time data is meaningless without a schedule to compare it to.** "This bus is 4 minutes late" only makes sense if you already know when it was scheduled to arrive. Static GTFS is that schedule. Building the real-time layer first would have nothing to check itself against.
- **Static GTFS is a much smaller problem.** It's a periodic download-and-parse job — no continuous polling, no rate limits to manage, and typically no API key required. Real-time feeds (GTFS-Realtime, CTA's Bus/Train Tracker) require constant polling, API keys, and merging against the schedule to be useful at all.
- **It proves the ingestion pipeline works before adding live-polling complexity on top.** If static GTFS ingestion and the resulting metrics are solid, the real-time layer becomes "add polling and a cache," not "build data ingestion for the first time under time pressure."
- **It lets today's manual estimates be checked against something real.** Right now, `wait_transfer_minutes` and `transfers` in `trip_scenarios` are hand-guessed. Static GTFS gives an actual, computed answer to compare them against, before ever touching live data.

## 2. What GTFS Is, in Plain English

GTFS (General Transit Feed Specification) is a standard file format transit agencies use to publish their scheduled service. It's a `.zip` file containing several plain text files that behave like CSVs — no special tools required to read them, just Python's built-in `csv` module. Because every agency publishes the same file shapes, one ingestion script can work for both DART and CTA, with only the download URL differing.

The core files, in plain English:

| File | What it means |
|---|---|
| `agency.txt` | Who runs the service (DART, CTA) |
| `routes.txt` | The bus/train lines themselves (e.g. "Red Line") |
| `trips.txt` | One scheduled run of a route (e.g. "the 7:14am Red Line train toward downtown") |
| `stop_times.txt` | What time a given trip is scheduled to be at a given stop |
| `stops.txt` | Physical stop/station locations (name, latitude, longitude) |
| `calendar.txt` | Which days of the week a trip runs (weekdays only, weekends only, etc.) |
| `calendar_dates.txt` | Exceptions to `calendar.txt` — added or removed service on specific dates, like holidays |

These field and file names come directly from the GTFS spec itself, not something invented for this project — so the ingestion code ends up mapping almost one-to-one onto the raw CSV columns.

## 3. Target Agencies

- **DART** (Dallas Area Rapid Transit) — serves Dallas
- **CTA** (Chicago Transit Authority) — serves Chicago

These two match the two cities already represented in the manual sample data, so this integration deepens the existing scope rather than expanding it to new cities. Both agencies publish open GTFS static feeds through their own developer/open-data pages. The exact current download URL for each should be confirmed directly from each agency's developer site at build time rather than assumed here, since feed URLs can change.

## 4. Proposed Ingestion Flow

1. Download the GTFS zip — either placed manually during development, or fetched from a configured URL (one config value per agency, not hardcoded into the parsing logic).
2. Unzip it into its component `.txt` files.
3. Parse each file with Python's built-in `csv` module — no new heavy dependency (like pandas) needed for this.
4. Insert normalized rows into the new `gtfs_*` SQLite tables (below).
5. Once loaded, compute derived service metrics (headways, frequency, per-route counts) with SQL aggregate queries — the same pattern already used in `dashboard_repository.py`.

This mirrors the shape of `scripts/seed_db.py`: read a file, parse it, load it into SQLite. The difference is scale and source — a real, periodically-republished agency feed instead of 12 hand-typed JSON rows.

## 5. Proposed SQLite Tables

| Table | Holds | Key columns |
|---|---|---|
| `gtfs_agencies` | One row per transit agency | `agency_id`, `agency_name`, `agency_url`, `agency_timezone` |
| `gtfs_routes` | Bus/train lines | `route_id`, `agency_id` (FK), `route_short_name`, `route_long_name`, `route_type` |
| `gtfs_stops` | Physical stop locations | `stop_id`, `stop_name`, `stop_lat`, `stop_lon` |
| `gtfs_trips` | Individual scheduled runs of a route | `trip_id`, `route_id` (FK), `service_id`, `trip_headsign`, `direction_id` |
| `gtfs_stop_times` | What time each trip hits each stop | `trip_id` (FK), `stop_id` (FK), `arrival_time`, `departure_time`, `stop_sequence` |
| `gtfs_calendar` | Which days of the week each service pattern runs | `service_id`, `monday`...`sunday` (0/1 flags), `start_date`, `end_date` |
| `gtfs_calendar_dates` | Exceptions to `gtfs_calendar` (holidays, etc.) | `service_id`, `date`, `exception_type` |

Every table also gets its own `id INTEGER PRIMARY KEY`, same as `trip_scenarios` — the `*_id` columns above are the identifiers from the GTFS feed itself, kept as plain text/number columns rather than reused as the primary key, since GTFS IDs aren't guaranteed to be simple integers.

## 6. First Useful Metrics

Once the tables above are populated, these are the first metrics worth computing — all via SQL aggregate queries, the same style as the existing dashboard:

- **Routes per agency** — `COUNT(*)` grouped by agency.
- **Stops per route** — join `stop_times` → `trips` → `routes`, count distinct stops per route.
- **Trips per route** — count of scheduled trips per route, optionally filtered to trips active on a given day via `gtfs_calendar`.
- **Approximate headway by route/time window** — at a representative stop, look at the gap between consecutive scheduled departure times within a window (e.g. weekday 7–9am), and average or take the median gap. This is the real, computed version of what `wait_transfer_minutes` currently approximates by hand.
- **Service frequency near selected route scenarios** — for an existing manual route (e.g. "Dallas suburb → Downtown Dallas"), find nearby GTFS stops by latitude/longitude and report how many trips per hour pass through them, as a sanity check against the manual estimate.

## 7. How This Connects to Current Route Analysis

`RouteScenario` and `trip_scenarios` don't need to change shape. Today, `wait_transfer_minutes`, `transfers`, and similar fields are manually guessed placeholder values. Once GTFS metrics exist, those same fields could be filled in with real, computed numbers for Dallas and Chicago routes — the existing `scoring.py` (transit penalty, car dependency score) and `simulator.py` (improvement recommendations) would keep working unchanged, just fed better-sourced inputs. This is a data-quality upgrade, not an architecture change.

Longer term, GTFS data could let users search real stop pairs instead of the current fixed set of 12 scenarios — but that depends on a stop-matching step that isn't part of this milestone.

## 8. Future Real-Time Layer

Once static GTFS ingestion is solid, later work could add:

- **CTA Bus Tracker / Train Tracker** — CTA's own real-time arrival-prediction APIs, agency-specific (not the standardized GTFS-Realtime format), each requiring a free developer API key.
- **CTA GTFS-Realtime** — CTA's standardized real-time feed (vehicle positions, trip updates, service alerts), which reuses the same GTFS-family parsing approach.
- **DART GTFS-Realtime** — DART's equivalent standardized real-time feed.
- **API keys stored in the backend `.env` only** — never committed, never sent to or used by the frontend. The frontend never calls these APIs directly; only the backend does, so keys stay server-side.
- **Cache-first external calls** — any of these real-time calls should go through the `route_lookup_cache` design in [docs/caching-plan.md](caching-plan.md), with a short TTL appropriate for live data (minutes, not days or weeks).

## 9. V2 Implementation Checklist

1. Confirm the current GTFS static download URL for DART and for CTA directly from each agency's developer/open-data page — don't hardcode an assumed URL into code or docs ahead of time.
2. Add the seven `gtfs_*` tables to `database.py`, following the same `CREATE TABLE IF NOT EXISTS` pattern already used for `trip_scenarios`.
3. Write a CSV parser for each GTFS file type using Python's built-in `csv` module.
4. Write an ingestion script (e.g. `scripts/seed_gtfs.py`) that downloads or reads a local GTFS zip, parses it, and loads all seven tables — parameterized so it can run once per agency.
5. Run it once for DART and once for CTA; sanity-check the row counts (CTA in particular should have far more stops and trips than the current 12 manual routes).
6. Add a `gtfs_repository.py` with the aggregate queries from section 6, following the same pattern as `route_repository.py` and `dashboard_repository.py`.
7. Add pytest tests using a small, hand-written GTFS-shaped fixture (a few fake rows, not a real downloaded feed) so tests stay fast — the same temporary-database pattern already used in `test_route_repository.py` and `test_dashboard_repository.py`.
8. Only after static ingestion is working and tested, evaluate GTFS-Realtime or agency-specific real-time APIs, applying the cache-first design from `docs/caching-plan.md`.
9. Decide how static ingestion gets re-run over time — agencies republish GTFS every few weeks or months, and re-running the ingestion script manually is a reasonable starting point before building any scheduled/automated refresh.

## 10. Explicitly Out of Scope (for This GTFS Milestone)

- **Arbitrary Google Maps-style routing.** GTFS describes scheduled transit service, not turn-by-turn driving directions or multi-modal trip planning between arbitrary addresses. That's a separate, later integration (see the Google Maps/OpenRouteService mention in `docs/caching-plan.md`).
- **Perfect door-to-door directions.** Walking directions to/from a stop, or routing between two arbitrary addresses, is out of scope here. This milestone is about schedule data and aggregate metrics, not trip planning.
- **Real-time predictions in the first GTFS milestone.** Static GTFS only. No Bus Tracker, Train Tracker, or GTFS-Realtime work happens until static ingestion is proven and stable.
- **Frontend map rendering.** No map component (Leaflet, Mapbox, Google Maps) in this milestone. Metrics surface as numbers and lists, consistent with the existing dashboard — not a map view.
