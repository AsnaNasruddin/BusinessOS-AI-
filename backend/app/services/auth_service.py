"""Business logic for Module 1 (Authentication). Routes stay thin — they parse
the request, call a service function, and shape the response; every actual
decision lives here so it's testable without spinning up FastAPI."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import User
from app.services import org_service
from app.services.security import hash_password, verify_password


class EmailAlreadyRegisteredError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


async def register_user(
    db: AsyncSession, *, email: str, password: str, full_name: str
) -> tuple[User, "org_service.OrgWithRole"]:
    """Creates the user and a personal organization they own — nobody ends up
    registered-but-orgless, since every business-scoped resource requires an
    org (Section 12, rule 7)."""
    existing = await db.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none() is not None:
        raise EmailAlreadyRegisteredError(email)

    user = User(email=email, hashed_password=hash_password(password), full_name=full_name)
    db.add(user)
    await db.flush()  # assigns user.id without committing yet

    org_with_role = await org_service.create_org(db, owner=user, name=f"{full_name}'s Workspace")

    await db.refresh(user)
    return user, org_with_role


async def authenticate_user(db: AsyncSession, *, email: str, password: str) -> User:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(password, user.hashed_password):
        raise InvalidCredentialsError()
    return user
