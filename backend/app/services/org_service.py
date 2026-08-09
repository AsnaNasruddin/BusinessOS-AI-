"""Business logic for Module 2 (Organizations & Memberships)."""

import re
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Membership, Organization, User
from app.services.security import (
    InvalidTokenError,
    create_invite_token,
    decode_invite_token,
    hash_password,
)
from app.workflow_generation.planner import ensure_planner_agent


@dataclass
class OrgWithRole:
    org: Organization
    role: str


class UserAlreadyMemberError(Exception):
    pass


class InvalidInviteError(Exception):
    pass


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "org"


async def _unique_slug(db: AsyncSession, base: str) -> str:
    slug = base
    suffix = 2
    while True:
        result = await db.execute(select(Organization).where(Organization.slug == slug))
        if result.scalar_one_or_none() is None:
            return slug
        slug = f"{base}-{suffix}"
        suffix += 1


async def create_org(db: AsyncSession, *, owner: User, name: str) -> OrgWithRole:
    slug = await _unique_slug(db, _slugify(name))
    org = Organization(name=name, slug=slug)
    db.add(org)
    await db.flush()

    membership = Membership(user_id=owner.id, org_id=org.id, role="owner")
    db.add(membership)
    await db.flush()

    # Every org needs its own Workflow Planner agent for the NL workflow
    # generator to work at all (§16.6) — seeded here, the one choke point
    # every org-creation path (registration, POST /orgs) already goes
    # through, so no org is ever silently missing it.
    await ensure_planner_agent(db, org_id=org.id)

    return OrgWithRole(org=org, role="owner")


async def list_user_orgs(db: AsyncSession, *, user: User) -> list[OrgWithRole]:
    result = await db.execute(
        select(Membership, Organization)
        .join(Organization, Membership.org_id == Organization.id)
        .where(Membership.user_id == user.id)
    )
    return [OrgWithRole(org=org, role=membership.role) for membership, org in result.all()]


async def get_org_members(db: AsyncSession, *, org_id: uuid.UUID) -> list[tuple[User, str]]:
    result = await db.execute(
        select(User, Membership.role)
        .join(Membership, Membership.user_id == User.id)
        .where(Membership.org_id == org_id)
    )
    return list(result.all())


async def create_invite(db: AsyncSession, *, org_id: uuid.UUID, email: str, role: str) -> str:
    """Returns a signed invite token — see security.create_invite_token for
    why there's no pending-invite table. Raises UserAlreadyMemberError if the
    email already belongs to a member of this org."""
    existing_result = await db.execute(select(User).where(User.email == email))
    existing_user = existing_result.scalar_one_or_none()
    if existing_user is not None:
        already_member = (
            await db.execute(
                select(Membership).where(
                    Membership.org_id == org_id, Membership.user_id == existing_user.id
                )
            )
        ).scalar_one_or_none()
        if already_member is not None:
            raise UserAlreadyMemberError(email)

    return create_invite_token(org_id, email, role)


async def accept_invite(
    db: AsyncSession,
    *,
    invite_token: str,
    full_name: str | None,
    password: str | None,
) -> tuple[User, Organization]:
    """Completes an invite: creates the Membership, and — if the invited
    email has no account yet — registers the user in the same step (using
    the full_name/password supplied alongside the token)."""
    try:
        claims = decode_invite_token(invite_token)
    except InvalidTokenError as exc:
        raise InvalidInviteError(str(exc)) from exc

    org = await db.get(Organization, claims["org_id"])
    if org is None:
        raise InvalidInviteError("Organization no longer exists.")

    user_result = await db.execute(select(User).where(User.email == claims["email"]))
    user = user_result.scalar_one_or_none()

    if user is None:
        if not full_name or not password:
            raise InvalidInviteError(
                "No account exists for this email yet — full_name and password are required."
            )
        user = User(
            email=claims["email"],
            hashed_password=hash_password(password),
            full_name=full_name,
        )
        db.add(user)
        await db.flush()

    existing_membership = (
        await db.execute(
            select(Membership).where(Membership.org_id == org.id, Membership.user_id == user.id)
        )
    ).scalar_one_or_none()
    if existing_membership is None:
        db.add(Membership(user_id=user.id, org_id=org.id, role=claims["role"]))
        await db.flush()

    await db.refresh(user)
    return user, org
