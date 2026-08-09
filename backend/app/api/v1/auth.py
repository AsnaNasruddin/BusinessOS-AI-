from fastapi import APIRouter, HTTPException, status

from app.database.models import User
from app.deps import CurrentUser, DbSession
from app.schemas.auth import (
    AccessTokenOnly,
    LoginRequest,
    MembershipSummary,
    MeResponse,
    RefreshRequest,
    RegisterRequest,
    TokenPair,
    UserOut,
)
from app.services import auth_service, org_service
from app.services.security import (
    InvalidTokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
)

router = APIRouter()


@router.post("/register", response_model=TokenPair, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: DbSession) -> TokenPair:
    try:
        user, _org_with_role = await auth_service.register_user(
            db, email=body.email, password=body.password, full_name=body.full_name
        )
    except auth_service.EmailAlreadyRegisteredError as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "An account with this email already exists."
        ) from exc

    return TokenPair(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/login", response_model=TokenPair)
async def login(body: LoginRequest, db: DbSession) -> TokenPair:
    try:
        user = await auth_service.authenticate_user(db, email=body.email, password=body.password)
    except auth_service.InvalidCredentialsError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password.") from exc

    return TokenPair(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/refresh", response_model=AccessTokenOnly)
async def refresh(body: RefreshRequest, db: DbSession) -> AccessTokenOnly:
    try:
        user_id = decode_token(body.refresh_token, expected_type="refresh")
    except InvalidTokenError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc

    # Re-check the user still exists — a deleted account shouldn't be able to
    # keep refreshing for the rest of the refresh token's 7-day life.
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User no longer exists.")

    return AccessTokenOnly(access_token=create_access_token(user_id))


@router.get("/me", response_model=MeResponse)
async def me(current_user: CurrentUser, db: DbSession) -> MeResponse:
    orgs_with_roles = await org_service.list_user_orgs(db, user=current_user)
    return MeResponse(
        user=UserOut.model_validate(current_user),
        memberships=[
            MembershipSummary(
                org_id=owr.org.id, org_name=owr.org.name, org_slug=owr.org.slug, role=owr.role
            )
            for owr in orgs_with_roles
        ],
    )
