# Model modules register themselves here as phases add them (Section 6):
# user.py, org.py, agent.py, kb.py, workflow.py, tool.py, memory.py, log.py.
# Empty in Phase 0 — Auth + Orgs (Phase 1) adds the first models.
from app.database.models.base import Base

__all__ = ["Base"]
