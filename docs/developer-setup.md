# Developer Setup

Detailed setup steps for Transit Improvement Lab. For the project overview, see the root [README](../README.md).

## Prerequisites

- Python 3.10+ (developed against 3.12)
- Node.js 18+ and npm

## Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python scripts/seed_db.py
./run.sh                        # or: uvicorn app.main:app --reload
```

The API runs at `http://localhost:8000`. FastAPI's interactive docs are available at `http://localhost:8000/docs`.

## Frontend

```bash
cd frontend
npm install
npm run dev
```

The app runs at `http://localhost:5173`. It requires the backend running on port 8000 — CORS in `backend/app/main.py` is locked to that origin.

## Tests and checks

Backend (from `backend/`, with the virtual environment activated):

```bash
pytest
```

Frontend (from `frontend/`):

```bash
npx tsc --noEmit
npm run lint
npm run build
```

## Regenerating the database

`backend/transit_lab.db` is generated, not checked into git. If you pull changes to `data/sample-routes.json`, or the database file is missing or stale, re-run:

```bash
cd backend
source venv/bin/activate
python scripts/seed_db.py
```

This clears and reloads the `trip_scenarios` table — safe to run repeatedly. The JSON file is only read by this script; the running API reads from SQLite.

## Project layout

```text
backend/
  app/
    main.py                  FastAPI app + CORS setup
    database.py               SQLite connection + schema
    schemas.py                  Pydantic models (API request/response shapes)
    repositories/
      route_repository.py       All SQL lives here
    routes/
      route_scenarios.py          API endpoint handlers
    services/
      data_loader.py                Parses data/sample-routes.json (seed script only)
      scoring.py                      Transit penalty, car dependency, emissions
      simulator.py                     Rule-based improvement recommendation
  scripts/
    seed_db.py                  Seeds transit_lab.db from sample-routes.json
  tests/                       Pytest suite

frontend/
  src/
    App.tsx                    Search / select / analyze UI
    api.ts                       fetch() calls to the backend
    types.ts                      TypeScript types matching the Pydantic schemas

data/
  sample-routes.json          Manual V1 seed data (not read live by the API)
```

## Known rough edges

- Route data is hand-estimated, not sourced from GTFS, DART, or CTA — see the root README's [Data & Accuracy](../README.md#data--accuracy) section.
- No database migrations yet; schema changes currently require deleting `transit_lab.db` and re-seeding.
- No authentication or deployment setup yet — local development only.
