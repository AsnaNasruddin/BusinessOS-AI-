from fastapi import APIRouter

from app.deps import CurrentOrg, DbSession
from app.schemas.dashboard import DashboardStatsOut
from app.services import dashboard_service

router = APIRouter()


@router.get("/stats", response_model=DashboardStatsOut)
async def get_dashboard_stats(ctx: CurrentOrg, db: DbSession) -> DashboardStatsOut:
    return await dashboard_service.get_dashboard_stats(db, org_id=ctx.org.id)
