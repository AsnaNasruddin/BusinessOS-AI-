# Every model module registers on Base here as phases add it (Section 6):
# user.py, org.py (Phase 1); agent.py, kb.py, workflow.py, tool.py, memory.py,
# log.py (Phase 2+). Alembic's autogenerate reads Base.metadata, so a model
# that isn't imported here is invisible to migrations.
from app.database.models.agent import Agent
from app.database.models.approval import Approval
from app.database.models.base import Base
from app.database.models.kb import KbDocument, KnowledgeBase
from app.database.models.memory import AgentMemory
from app.database.models.org import Membership, Organization
from app.database.models.user import User
from app.database.models.workflow import Workflow, WorkflowRun, WorkflowStep

__all__ = [
    "Base",
    "User",
    "Organization",
    "Membership",
    "Agent",
    "KnowledgeBase",
    "KbDocument",
    "Workflow",
    "WorkflowRun",
    "WorkflowStep",
    "Approval",
    "AgentMemory",
]
