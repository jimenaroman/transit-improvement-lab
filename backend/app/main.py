from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.dashboard import router as dashboard_router
from app.routes.gtfs import router as gtfs_router
from app.routes.route_scenarios import router as route_scenarios_router


app = FastAPI(
    title="Transit Improvement Lab API",
    description="API for comparing transit trips, car dependency, and improvement scenarios.",
    version="0.1.0",
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
