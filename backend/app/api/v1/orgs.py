from fastapi import APIRouter, HTTPException, status

from app.deps import CurrentOrgFromPath, CurrentUser, DbSession
from app.schemas.auth import TokenPair
from app.schemas.org import (
    AcceptInviteRequest,
    InviteRequest,
    InviteResponse,
    MemberOut,
    OrgCreate,
    OrgDetail,
    OrgOut,
)
from app.services import org_service
from app.services.security import create_access_token, create_refresh_token

router = APIRouter()

_MANAGE_MEMBERS_ROLES = {"owner", "admin"}


@router.get("", response_model=list[OrgOut])
async def list_orgs(current_user: CurrentUser, db: DbSession) -> list[OrgOut]:
    orgs_with_roles = await org_service.list_user_orgs(db, user=current_user)
    return [
        OrgOut(
            id=owr.org.id,
            name=owr.org.name,
            slug=owr.org.slug,
            created_at=owr.org.created_at,
            my_role=owr.role,
        )
        for owr in orgs_with_roles
    ]


@router.post("", response_model=OrgOut, status_code=status.HTTP_201_CREATED)
async def create_org(body: OrgCreate, current_user: CurrentUser, db: DbSession) -> OrgOut:
    owr = await org_service.create_org(db, owner=current_user, name=body.name)
    return OrgOut(
        id=owr.org.id,
        name=owr.org.name,
        slug=owr.org.slug,
        created_at=owr.org.created_at,
        my_role=owr.role,
    )


@router.get("/{org_id}", response_model=OrgDetail)
async def get_org(ctx: CurrentOrgFromPath, db: DbSession) -> OrgDetail:
    members = await org_service.get_org_members(db, org_id=ctx.org.id)
    return OrgDetail(
        id=ctx.org.id,
        name=ctx.org.name,
        slug=ctx.org.slug,
        created_at=ctx.org.created_at,
        my_role=ctx.role,
        members=[
            MemberOut(user_id=user.id, email=user.email, full_name=user.full_name, role=role)
            for user, role in members
        ],
    )


@router.post(
    "/{org_id}/members", response_model=InviteResponse, status_code=status.HTTP_201_CREATED
)
async def invite_member(
    body: InviteRequest, ctx: CurrentOrgFromPath, db: DbSession
) -> InviteResponse:
    if ctx.role not in _MANAGE_MEMBERS_ROLES:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only owners and admins can invite members.")

    try:
        token = await org_service.create_invite(
            db, org_id=ctx.org.id, email=body.email, role=body.role
        )
    except org_service.UserAlreadyMemberError as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "This person is already a member of the organization."
        ) from exc

    return InviteResponse(invite_token=token, invite_link=f"/accept-invite?token={token}")


@router.post("/accept-invite", response_model=TokenPair)
async def accept_invite(body: AcceptInviteRequest, db: DbSession) -> TokenPair:
    try:
        user, _org = await org_service.accept_invite(
            db,
            invite_token=body.invite_token,
            full_name=body.full_name,
            password=body.password,
        )
    except org_service.InvalidInviteError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    return TokenPair(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )
