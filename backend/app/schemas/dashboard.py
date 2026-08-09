from pydantic import BaseModel


class DashboardStatsOut(BaseModel):
    active_workflows: int
    total_workflows: int
    runs_24h: int
    success_rate_7d: float
    tokens_30d: int
    est_cost_30d: float
    cost_note: str
