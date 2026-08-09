"""Phase 8 — real aggregates for the Dashboard page, which had been reading
frontend/src/lib/seed-data.ts's fixed mock numbers since the frontend
scaffold was first built, long before there was a backend to ask."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Workflow, WorkflowRun
from app.schemas.dashboard import DashboardStatsOut


async def get_dashboard_stats(db: AsyncSession, *, org_id: uuid.UUID) -> DashboardStatsOut:
    now = datetime.now(UTC)
    day_ago = now - timedelta(hours=24)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    workflows = (
        await db.execute(select(Workflow.is_active).where(Workflow.org_id == org_id))
    ).scalars().all()
    total_workflows = len(workflows)
    active_workflows = sum(1 for is_active in workflows if is_active)

    runs_24h = (
        await db.execute(
            select(func.count())
            .select_from(WorkflowRun)
            .where(WorkflowRun.org_id == org_id, WorkflowRun.started_at >= day_ago)
        )
    ).scalar_one()

    week_statuses = (
        await db.execute(
            select(WorkflowRun.status).where(
                WorkflowRun.org_id == org_id,
                WorkflowRun.started_at >= week_ago,
                WorkflowRun.status.in_(["succeeded", "failed"]),
            )
        )
    ).scalars().all()
    success_rate_7d = (
        round(100 * sum(1 for s in week_statuses if s == "succeeded") / len(week_statuses), 1)
        if week_statuses
        else 0.0
    )

    month_rows = (
        await db.execute(
            select(WorkflowRun.total_tokens, WorkflowRun.total_cost_usd).where(
                WorkflowRun.org_id == org_id, WorkflowRun.started_at >= month_ago
            )
        )
    ).all()
    tokens_30d = sum(tokens for tokens, _cost in month_rows)
    est_cost_30d = sum(cost for _tokens, cost in month_rows)
    cost_note = _cost_note(month_rows)

    return DashboardStatsOut(
        active_workflows=active_workflows,
        total_workflows=total_workflows,
        runs_24h=runs_24h,
        success_rate_7d=success_rate_7d,
        tokens_30d=tokens_30d,
        est_cost_30d=est_cost_30d,
        cost_note=cost_note,
    )


def _cost_note(month_rows: list) -> str:
    if not month_rows:
        return "No runs in the last 30 days"
    paid_runs = sum(1 for _tokens, cost in month_rows if cost > 0)
    free_runs = len(month_rows) - paid_runs
    if paid_runs == 0:
        return "All runs on Ollama (free)"
    if free_runs == 0:
        return f"{paid_runs} run(s) used a paid provider"
    return f"{paid_runs} run(s) used a paid provider · {free_runs} on Ollama (free)"
