import uuid

from sqlalchemy import Select, select


def scoped_query(model: type, org_id: uuid.UUID) -> Select:
    """Every business-scoped query must go through this (Section 12, rule 7).
    Assumes `model` has an `org_id` column — Agent, Workflow, KnowledgeBase,
    etc. from Phase 2 onward. Not used by User/Organization/Membership
    themselves, which aren't org-scoped resources in that sense."""
    return select(model).where(model.org_id == org_id)
