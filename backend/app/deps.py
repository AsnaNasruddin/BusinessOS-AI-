"""Shared FastAPI dependencies.

Phase 0 only has `get_db`. Phase 1 (Auth + Orgs) adds `get_current_user` and
`get_current_org` here, and a `scoped_query()` helper goes in app/utils/ —
Section 12, rule 7: every DB query in a business route must filter by org_id.
"""

from app.database.session import get_db

__all__ = ["get_db"]
