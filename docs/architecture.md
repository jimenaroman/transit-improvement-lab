# Architecture

This document defines where backend code belongs in Transit Improvement Lab. When adding code, follow this doc instead of improvising a new structure. If something genuinely doesn't fit one of these categories, propose the change here first — don't create a new top-level folder or pattern ad hoc.

## `backend/app/routes/`

FastAPI endpoints only.

- Validate the request (path/query params, request body via Pydantic).
- Call one or more repository or service functions.
- Return the response — FastAPI serializes it via `response_model`.
- No SQL. No business logic or calculations. No file I/O.

Examples: `route_scenarios.py`, `dashboard.py`, `gtfs.py`.

## `backend/app/repositories/`

Database access only.

- Every SQL query in the codebase lives here — nowhere else should contain a SQL string.
- Functions take plain arguments and return typed values (schema objects, primitives) — never a raw `sqlite3.Row`, and never an HTTP request/response object.
- No business logic (scoring, recommendations, calculations) — that belongs in `services/`.
- One repository file per feature/data-access concern, not strictly one per table. `dashboard_repository.py` and `route_repository.py` both read `trip_scenarios` but serve different callers; `gtfs_repository.py` (import-time writes) and `gtfs_summary_repository.py` (read-only endpoint queries) is the same split, even though both touch the `gtfs_*` tables.

Examples: `route_repository.py`, `dashboard_repository.py`, `gtfs_repository.py`, `gtfs_summary_repository.py`.

## `backend/app/services/`

Business logic and calculations.

- No FastAPI request/response objects. No SQL or direct database access.
- Takes and returns plain Python/Pydantic values, so it's testable without a database or a running server.

Examples: `scoring.py` (transit penalty, car dependency score), `simulator.py` (improvement recommendations).

## `backend/scripts/`

One-off CLI utilities, run manually from a terminal — never imported by the running API.

- Argument parsing (`argparse`), file I/O, and orchestration. The actual work still goes through repository/service functions, not raw SQL written inline in the script.

Examples: `seed_db.py`, `import_gtfs.py`.

## `backend/app/schemas.py`, `backend/app/gtfs_schemas.py`

Pydantic request/response models only.

- No logic beyond field definitions and Pydantic validation.
- Split by domain when one file would get too broad. `schemas.py` covers the app's own route scenarios, comparisons, and dashboard; `gtfs_schemas.py` covers imported GTFS data, kept separate since it describes a different data source with different shapes.

## `backend/app/database.py`

SQLite connection and table schema only.

- `get_connection()`, `init_db()`, and `CREATE TABLE` statements.
- No `SELECT`/`INSERT`/`UPDATE`/`DELETE` here — those belong in `repositories/`.

## `backend/tests/`

Mirrors the layers above, each tested in isolation:

- **Repository tests** — always against a temporary SQLite file (`monkeypatch.setattr(database, "DB_PATH", ...)`), never the real `backend/transit_lab.db`.
- **Endpoint tests** — via FastAPI's `TestClient`, checking status codes, routing, and request validation on top of already-tested repository logic. They shouldn't re-prove business logic the repository/service tests already cover.
- **Service tests** — plain `RouteScenario` objects in, plain return values out. No database, no HTTP.

## Rule for adding new code

Before creating a new top-level folder or a new pattern, check whether it fits one of the categories above. If it doesn't, that's worth a conversation before writing code, not a decision to make silently.
