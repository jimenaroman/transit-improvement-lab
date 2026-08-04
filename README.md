# Transit Improvement Lab

Transit Improvement Lab is a full-stack web app that compares driving and public-transit trips, calculates car dependency, estimates commute costs, and simulates which transit improvements would save the most time.

## Why I'm Building This

I grew up in the Dallas area, where public transit often felt limited to special trips (like going to the Texas State Fair) rather than everyday mobility. After living in Chicago, where I could use buses and trains to go downtown, cross the city, and reach the airport, I wanted to better reason what makes transit usable in one place and difficult in another.

This project studies common route scenarios and asks:

- How much longer does public transit take compared with driving?
- How much time is lost to waiting, walking, and transfers?
- Which service improvements would reduce commute burden the most?
- How do Dallas and Chicago differ across similar trip types?

## Current Features

- 12 manual V1 route scenarios across Dallas and Chicago
- Search and filter scenarios by city, origin, or destination
- Select a scenario and analyze it on demand
- Transit penalty calculation (transit time ÷ driving time)
- Car dependency score (a 0–100 heuristic, see below)
- Weekly extra transit time estimate
- Emissions comparison (driving vs. transit)
- Rule-based improvement recommendation with a simulated before/after estimate

Not yet built: a commute cost calculator and a summary dashboard (see [Roadmap](#roadmap)).

## Tech Stack

- Frontend: React, TypeScript, Vite
- Backend: FastAPI, Python
- Database: SQLite (V1 data layer)
- Data: Manual V1 sample route scenarios — see [Data & Accuracy](#data--accuracy)
- Testing: Pytest (backend), ESLint + `tsc` (frontend)

## Architecture

```text
React + TypeScript frontend (Vite)
        ↓  fetch()
FastAPI backend
        ↓
SQLite database (trip_scenarios table)
        ↓
Python scoring and simulation services
        ↓
Route search, analysis, and comparison UI
```

## Data & Accuracy

Route data in this project — distances, drive/transit times, fares, emissions — is **manually estimated for V1**, not sourced from GTFS, DART, CTA, or any official transit API. It exists to test the app's data flow and UI end to end before real transit data is integrated. Every route's `notes` field says so explicitly (`"Manual V1 sample estimate; verify before research use."`). Treat all numbers here as placeholders, not research-grade figures.

## Getting Started

### Backend setup

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python scripts/seed_db.py   # creates/refreshes backend/transit_lab.db from data/sample-routes.json
./run.sh                    # starts the API on http://localhost:8000
```

### Frontend setup

```bash
cd frontend
npm install
npm run dev                 # starts the dev server on http://localhost:5173
```

The backend must be running on port 8000 for the frontend to load data — CORS is configured for `http://localhost:5173` in `backend/app/main.py`.

### Running tests

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

See [docs/developer-setup.md](docs/developer-setup.md) for a more detailed setup and project-structure reference.

## Data Layer

SQLite is the V1 data layer. Route scenarios are seeded from `data/sample-routes.json` into `backend/transit_lab.db`, which is gitignored, generated, and never edited directly.

To create or refresh the database after changing `sample-routes.json`:

```bash
cd backend
source venv/bin/activate
python scripts/seed_db.py
```

This clears and reloads the `trip_scenarios` table, so it's safe to re-run any time.

## API Endpoints

```text
GET /health
GET /api/routes
GET /api/routes?city=Dallas
GET /api/routes/{route_id}
GET /api/routes/{route_id}/comparison
```

## Roadmap

**Done:**
1. FastAPI backend with route and comparison endpoints
2. React + TypeScript frontend with search/select/analyze flow
3. SQLite data layer replacing the JSON file at runtime
4. 12 manual sample route scenarios across Dallas and Chicago

**Next (V1):**
5. README and developer setup docs (this milestone)
6. Basic dashboard: total route count, average transit penalty, highest car dependency score, worst wait/transfer burden, filter by city/category

**Later (V2):**
7. CTA/DART research and real transit data ingestion
8. External route/search API integration (e.g. Google Maps)

Deeper design notes live in [docs/](docs/) (`v1-spec.md`, `system-design.md`, `data-model.md`) — some are still being filled in as the project evolves.

## Status

Backend and frontend are functional end to end on manual sample data, with a SQLite-backed API and a working search → select → analyze flow. Next up: a dashboard view, then real transit data.
