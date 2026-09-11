# Architecture

This document defines where backend code belongs in Transit Improvement Lab. When adding code, follow this doc instead of improvising a new structure. If something genuinely doesn't fit one of these categories, propose the change here first — don't create a new top-level folder or pattern ad hoc.

## `backend/app/routes/`

FastAPI endpoints only.

- Validate the request (path/query params, request body via Pydantic).
- Call one or more repository or service functions.
- Return the response — FastAPI serializes it via `response_model`.
- No SQL. No business logic or calculations. No file I/O.

Examples: `route_scenarios.py`, `dashboard.py`, `gtfs.py`, `trips.py`.

## `backend/app/repositories/`

Database access only.

- Every SQL query in the codebase lives here — nowhere else should contain a SQL string.
- Functions take plain arguments and return typed values (schema objects, primitives) — never a raw `sqlite3.Row`, and never an HTTP request/response object.
- No business logic (scoring, recommendations, calculations) — that belongs in `services/`.
- One repository file per feature/data-access concern, not strictly one per table. `dashboard_repository.py` and `route_repository.py` both read `trip_scenarios` but serve different callers; `gtfs_repository.py` (import-time writes) and `gtfs_summary_repository.py` (read-only endpoint queries) is the same split, even though both touch the `gtfs_*` tables.

Examples: `route_repository.py`, `dashboard_repository.py`, `gtfs_repository.py`, `gtfs_summary_repository.py`.

## `backend/app/clients/`

External API clients only.

- Wraps outbound HTTP calls to third-party services (e.g. Google Routes) via `httpx`.
- Returns parsed JSON (`dict`) or raises a typed exception on failure/timeout/malformed response — never a normalized app model. Normalization is a service-layer concern (see below).
- No SQL, no FastAPI request/response objects, no business logic or scoring.
- Reads secrets (API keys) via `app/config.py` only. Never logs a secret, never includes one in an exception message.

Examples: `google_routes_client.py`.

## `backend/app/config.py`

Environment variable loading only.

- Loads `.env` (via `python-dotenv`) and exposes typed getters for secrets/config (e.g. `get_google_maps_api_key()`, `get_database_path()`, `get_cta_gtfs_zip_path()`, `get_dart_gtfs_zip_path()`).
- No logic beyond reading and validating presence of env vars. Never logs a secret value.

## `backend/app/services/`

Business logic and calculations.

- No FastAPI request/response objects. No SQL or direct database access.
- Takes and returns plain Python/Pydantic values, so it's testable without a database or a running server.

Examples: `scoring.py` (transit penalty, car dependency score), `simulator.py` (improvement recommendations for curated `RouteScenario` rows), `trip_comparison.py` (normalizes raw Google Routes API JSON from `clients/` into internal trip-comparison models), `trip_bottleneck_analysis.py` (deterministic bottleneck classification and recommendations for an arbitrary Google-routed trip -- the live-trip counterpart to `simulator.py`, kept separate since it operates on `TransitSummary`/`DrivingSummary`, not `RouteScenario`).

## `backend/scripts/`

One-off CLI utilities, run manually from a terminal — never imported by the running API.

- Argument parsing (`argparse`), file I/O, and orchestration. The actual work still goes through repository/service functions, not raw SQL written inline in the script.

Examples: `seed_db.py`, `import_gtfs.py`.

## `backend/seed_data/`

Static curated data files the seed scripts load, not generated output.

- Committed to git (small, hand-curated) — unlike `transit_lab.db` or the GTFS zips, which are generated/external and gitignored.
- Referenced only via a path relative to `backend/` itself, so it travels with the backend wherever it's deployed. See "Production data lifecycle" below for why this matters.

Examples: `sample-routes.json`, `scenario-gtfs-links.json`.

## `backend/app/schemas.py`, `backend/app/gtfs_schemas.py`

Pydantic request/response models only.

- No logic beyond field definitions and Pydantic validation.
- Split by domain when one file would get too broad. `schemas.py` covers the app's own route scenarios, comparisons, and dashboard; `gtfs_schemas.py` covers imported GTFS data; `trip_compare_schemas.py` covers the arbitrary origin/destination Google Routes flow — kept separate since forcing that response onto the curated `RouteScenario`/`RouteComparison` shape would mean inventing fields (fare, emissions, city) that don't exist for an arbitrary trip.

## `backend/app/database.py`

SQLite connection and table schema only.

- `get_connection()`, `init_db()`, and `CREATE TABLE` statements.
- `DB_PATH` comes from `config.get_database_path()` (see the production data lifecycle section below) rather than a hardcoded path, so every repository automatically points at the configured database.
- `ensure_database_ready()` fails loudly (`RuntimeError`) if the configured database is missing or has no curated scenarios yet. Called once from `app/main.py`'s startup lifespan — never from a repository, and never at import time.
- No `SELECT`/`INSERT`/`UPDATE`/`DELETE` here — those belong in `repositories/`.

## `backend/app/bootstrap_production.py`

The one explicit, idempotent production data bootstrap command — see "Production data lifecycle" below for what it does and why it's separate from `scripts/`.

## `backend/tests/`

Mirrors the layers above, each tested in isolation:

- **Repository tests** — always against a temporary SQLite file (`monkeypatch.setattr(database, "DB_PATH", ...)`), never the real `backend/transit_lab.db`.
- **Endpoint tests** — via FastAPI's `TestClient`, checking status codes, routing, and request validation on top of already-tested repository logic. They shouldn't re-prove business logic the repository/service tests already cover.
- **Service tests** — plain `RouteScenario` objects in, plain return values out. No database, no HTTP.

## Production data lifecycle

Four things that are easy to conflate, kept deliberately distinct:

- **SOURCE CODE** (GitHub) — everything in this repo, including the small curated seed files under `backend/seed_data/` (`sample-routes.json`, `scenario-gtfs-links.json`). These ship with the backend deployment like any other source file — they are static application data, not generated output, so they live inside `backend/` rather than a monorepo-root `data/` directory a standalone backend deploy wouldn't have.
- **GENERATED DATA** (SQLite + imported GTFS) — `transit_lab.db`, produced by running the source code against external data. Never committed; gitignored (`backend/*.db`, `backend/*.db-journal`).
- **EXTERNAL DATA** (CTA/DART static GTFS feeds) — the zips in `data/gtfs/` for local dev, gitignored (`data/gtfs/**/*.zip`). This repo does not document an official download URL for either feed yet (see `docs/gtfs-integration-plan.md`); bootstrap reads them from a local path, never downloads them.
- **EXTERNAL SERVICES** (Google Places + Google Routes) — live API calls at request time, unrelated to the GTFS bootstrap; require `GOOGLE_MAPS_API_KEY`.

`backend/seed_data/` exists specifically because `app/services/data_loader.py` and `scripts/seed_scenario_gtfs_links.py` used to resolve these files via `Path(__file__).resolve().parents[N]` climbing past `backend/` into a monorepo-root `data/` directory. That works for a local checkout but not for a host (e.g. Railway) that builds only `backend/` as the service root — the climb silently lands somewhere else entirely (in one real case, inside the production volume mounted at `/data`). Every seed-file path now resolves relative to `backend/` itself and never climbs above it.

Local dev today:

```
GitHub code + local transit_lab.db (checked out by hand, not committed) → FastAPI
```

Production after this milestone:

```
GitHub
  → backend deployment
  → one-time data bootstrap (python -m app.bootstrap_production)
      → CTA/DART GTFS (from a local zip path, not downloaded)
      → existing importer + seed scripts
      → persistent SQLite DB
  → FastAPI (uvicorn app.main:app)
      ├── Google Places
      ├── Google Routes
      └── persistent GTFS SQLite (read-only from FastAPI's perspective)
  → React
```

`app/bootstrap_production.py` lives under `app/` instead of `scripts/` specifically so it can be invoked as `python -m app.bootstrap_production` — everywhere else, "one-off CLI utility" means `scripts/`. It is never imported by `app.main`, and `uvicorn` never triggers it: bootstrap and serving are two separate commands, run at two separate times, so a normal restart never re-imports GTFS.

### Environment variables

| Variable | Required in production | Local dev default |
|---|---|---|
| `GOOGLE_MAPS_API_KEY` | Yes | From `backend/.env` |
| `DATABASE_PATH` | Yes — must point at a persistent volume | `backend/transit_lab.db` if unset |
| `GTFS_CTA_ZIP_PATH` | Yes, until CTA's GTFS is already imported | Not needed once `transit_lab.db` already has CTA data |
| `GTFS_DART_ZIP_PATH` | Yes, until DART's GTFS is already imported | Not needed once `transit_lab.db` already has DART data |

### What must be persistent

The file at `DATABASE_PATH` must live on a persistent volume/directory that survives deploys and restarts — losing it means re-running bootstrap (a multi-minute GTFS re-import), not losing user data, but it should still not happen on every deploy. The GTFS zips at `GTFS_CTA_ZIP_PATH`/`GTFS_DART_ZIP_PATH` only need to exist for the bootstrap run itself; they don't need to persist afterward.

### Commands

Prepare the database (run once per environment, safe to re-run):

```
DATABASE_PATH=/data/transit_lab.db \
GTFS_CTA_ZIP_PATH=/data/gtfs/cta.zip \
GTFS_DART_ZIP_PATH=/data/gtfs/dart.zip \
python -m app.bootstrap_production
```

Launch the API (reads the same `DATABASE_PATH`; does no GTFS work itself):

```
DATABASE_PATH=/data/transit_lab.db uvicorn app.main:app --host 0.0.0.0 --port 8000
```

If `DATABASE_PATH` is absent or uninitialized when `uvicorn` starts, the app fails at startup with a clear `RuntimeError` naming the bootstrap command, instead of serving with silently-empty GTFS enrichment.

This is deliberately platform-neutral — no Render/Railway/Fly-specific config. On most platforms, the bootstrap command runs as a one-off/release-phase job against the same persistent volume the web process mounts, before the web process starts.

## Rule for adding new code

Before creating a new top-level folder or a new pattern, check whether it fits one of the categories above. If it doesn't, that's worth a conversation before writing code, not a decision to make silently.
