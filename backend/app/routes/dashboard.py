from fastapi import APIRouter

from app.repositories import dashboard_repository
from app.schemas import DashboardSummary

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def get_dashboard_summary() -> DashboardSummary:
    return dashboard_repository.get_summary()
