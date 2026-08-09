import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

Role = Literal["owner", "admin", "member"]


class OrgCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class OrgOut(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    created_at: datetime
    my_role: Role


class MemberOut(BaseModel):
    user_id: uuid.UUID
    email: EmailStr
    full_name: str
    role: Role


class OrgDetail(OrgOut):
    members: list[MemberOut]


class InviteRequest(BaseModel):
    email: EmailStr
    role: Role = "member"


class InviteResponse(BaseModel):
    """Section 7, Module 2: 'invite = a signed link in dev, not a real email.'
    The signed token IS the delivery mechanism here — in dev you copy this
    instead of checking an inbox."""

    invite_token: str
    invite_link: str


class AcceptInviteRequest(BaseModel):
    invite_token: str
    # Only required if the invited email doesn't have an account yet.
    full_name: str | None = None
    password: str | None = Field(default=None, min_length=8)
