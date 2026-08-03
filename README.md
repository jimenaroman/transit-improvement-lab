# Transit Improvement Lab

Transit Improvement Lab is a full-stack web app that compares driving and public-transit trips, calculates car dependency, estimates commute costs, and simulates which transit improvements would save the most time.

## Why I’m Building This

I grew up in the Dallas area, where public transit often felt limited to special trips (like going to the Texas State Fair) rather than everyday mobility. After living in Chicago, where I could use buses and trains to go downtown, cross the city, and reach the airport, I wanted to better reason what makes transit usable in one place and difficult in another.

This project studies common route scenarios and asks:

- How much longer does public transit take compared with driving?
- How much time is lost to waiting, walking, and transfers?
- Which service improvements would reduce commute burden the most?
- How do Dallas and Chicago differ across similar trip types?

## V1

- Route comparison between driving and public transit
- Transit penalty calculation
- Car dependency score
- Commute cost calculator
- Improvement simulator for route-level changes
- Basic dashboard of sample route scenarios

## Tech Stack

- Frontend: React, TypeScript, HTML/CSS
- Backend: FastAPI, Python
- Database: SQLite for V1
- Data: Manual sample route scenarios, with GTFS integration planned later
- Testing: Pytest

## Planned Architecture

React + TypeScript frontend
        ↓
FastAPI backend
        ↓
SQLite database
        ↓
Python scoring and simulation services
        ↓
Route comparison dashboard

## Current Status

Backend V0 is complete:
- GET /health
- GET /api/routes
- GET /api/routes/{route_id}
- GET /api/routes/{route_id}/comparison
- Pytest scoring tests passing
- Temporary JSON data source with future database layer planned