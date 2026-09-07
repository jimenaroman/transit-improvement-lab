from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import ensure_database_ready
from app.routes.dashboard import router as dashboard_router
from app.routes.gtfs import router as gtfs_router
from app.routes.places import router as places_router
from app.routes.route_scenarios import router as route_scenarios_router
from app.routes.trips import router as trips_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fails fast on a real boot if the DB wasn't bootstrapped -- not run
    # under TestClient(app) used without `with`, which is how every test
    # in this repo uses it, so this doesn't require a DB in tests.
    ensure_database_ready()
    yield


app = FastAPI(
    title="Transit Improvement Lab API",
    description="API for comparing transit trips, car dependency, and improvement scenarios.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(route_scenarios_router)
app.include_router(dashboard_router)
app.include_router(gtfs_router)
app.include_router(trips_router)
app.include_router(places_router)
