from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import agents, approvals, auth, kb, orgs, runs, tools, workflows
from app.config import get_settings

settings = get_settings()

app = FastAPI(
    title="BusinessOS AI",
    description="AI Operating System for business workflows.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root() -> dict[str, str]:
    return {"name": "BusinessOS AI", "status": "ok"}


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness check — Docker Compose and load balancers hit this, not `/`."""
    return {"status": "ok"}


app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(orgs.router, prefix="/api/v1/orgs", tags=["orgs"])
app.include_router(agents.router, prefix="/api/v1/agents", tags=["agents"])
app.include_router(tools.router, prefix="/api/v1/tools", tags=["tools"])
app.include_router(kb.router, prefix="/api/v1/kbs", tags=["knowledge-bases"])
app.include_router(workflows.router, prefix="/api/v1/workflows", tags=["workflows"])
app.include_router(runs.router, prefix="/api/v1/runs", tags=["runs"])
app.include_router(approvals.router, prefix="/api/v1/approvals", tags=["approvals"])

# Phase 6+ mounts routers here as they're built:
#   from app.api.v1 import dashboard, analytics
#   ...
