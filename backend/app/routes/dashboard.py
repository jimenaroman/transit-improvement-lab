from fastapi import APIRouter

from app.repositories import dashboard_repository, route_repository
from app.schemas import DashboardSummary, ResearchSummary
from app.services import research_analysis

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary() -> DashboardSummary:
    return dashboard_repository.get_summary()


@router.get("/research", response_model=ResearchSummary)
def get_dashboard_research() -> ResearchSummary:
    """
    Scenario-level data and simple aggregates/correlations for the Research
    page's exploratory charts. Reuses the same curated trip_scenarios sample
    and the same per-route transit_penalty calculation as /api/routes.
    """
    return research_analysis.build_research_summary(route_repository.list_routes())
