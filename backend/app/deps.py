"""Shared FastAPI dependencies.

`CurrentUser` decodes the JWT from the Authorization header. `CurrentOrg`
additionally requires an `X-Org-Id` header and verifies a Membership row
exists — this is the "JWT + org scope header" pattern the implementation
plan's API design (Section 8) calls for on every non-auth route. Business
routes (Phase 2+) should depend on `CurrentOrg`, not just `CurrentUser`, and
use `scoped_query()` (app/utils/db.py) for every query — Section 12, rule 7.

Everything is exposed as `Annotated[X, Depends(fn)]` aliases (FastAPI's
current recommended style) rather than `x: X = Depends(fn)` defaults — same
behavior, but it doesn't trip ruff's B008 (mutable-default-style) check, and
it's far less repetition across the many routes Phase 2+ adds.
"""

import uuid
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Membership, Organization, User
from app.database.session import get_db
from app.services.security import InvalidTokenError, decode_token

__all__ = [
    "DbSession",
    "CurrentUser",
    "CurrentOrg",
    "CurrentOrgFromPath",
    "CurrentOrgContext",
]

DbSession = Annotated[AsyncSession, Depends(get_db)]

_bearer = HTTPBearer(auto_error=False)


async def _get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    db: DbSession,
) -> User:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated.")

    try:
        user_id = decode_token(credentials.credentials, expected_type="access")
    except InvalidTokenError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc

    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User no longer exists.")
    return user


CurrentUser = Annotated[User, Depends(_get_current_user)]


@dataclass
class CurrentOrgContext:
    org: Organization
    role: str


async def _require_membership(
    org_id: uuid.UUID, current_user: User, db: AsyncSession
) -> CurrentOrgContext:
    result = await db.execute(
        select(Membership).where(Membership.user_id == current_user.id, Membership.org_id == org_id)
    )
    membership = result.scalar_one_or_none()
    if membership is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You are not a member of this organization.")

    org = await db.get(Organization, org_id)
    if org is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Organization not found.")

    return CurrentOrgContext(org=org, role=membership.role)


async def _get_current_org(
    current_user: CurrentUser,
    db: DbSession,
    x_org_id: Annotated[uuid.UUID, Header(alias="X-Org-Id")],
) -> CurrentOrgContext:
    """For business routes (Phase 2+) where the operating org is ambient
    context carried in a header — e.g. `GET /agents` needs to know which
    org's agents to list, and the org isn't part of that URL."""
    return await _require_membership(x_org_id, current_user, db)


CurrentOrg = Annotated[CurrentOrgContext, Depends(_get_current_org)]


async def _get_current_org_from_path(
    org_id: uuid.UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> CurrentOrgContext:
    """For routes where the org IS the resource in the URL —
    `GET /orgs/{org_id}`, `POST /orgs/{org_id}/members` — sourced from the
    path instead of a redundant header that would just have to match it."""
    return await _require_membership(org_id, current_user, db)


CurrentOrgFromPath = Annotated[CurrentOrgContext, Depends(_get_current_org_from_path)]
