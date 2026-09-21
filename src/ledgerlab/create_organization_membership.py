from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ledgerlab.current_user import get_authenticated_user
from ledgerlab.database import get_session
from ledgerlab.models import Organization, OrganizationMembership, User

router = APIRouter()


class CreateOrganizationMembershipRequest(BaseModel):
    user_id: UUID


class CreateOrganizationMembershipResponse(BaseModel):
    id: UUID
    role: str
    organization_id: UUID
    user_id: UUID
    created_at: datetime


@router.post(
    "/organizations/{organization_id}/memberships",
    status_code=201,
    response_model=CreateOrganizationMembershipResponse,
)
def create_organization_membership(
    organization_id: UUID,
    request: CreateOrganizationMembershipRequest,
    session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_authenticated_user)],
) -> CreateOrganizationMembershipResponse:

    organization = session.get(Organization, organization_id)
    if organization is None:
        raise HTTPException(
            status_code=404,
            detail="Organization not found",
        )

    user = session.get(User, request.user_id)
    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    existing_membership = (
        session.execute(
            select(OrganizationMembership).where(
                OrganizationMembership.organization_id == organization_id,
                OrganizationMembership.user_id == request.user_id,
            )
        )
    ).scalar_one_or_none()
    if existing_membership is not None:
        raise HTTPException(
            status_code=409,
            detail="Membership already exists",
        )

    organization_membership = OrganizationMembership(
        organization_id=organization_id,
        user_id=request.user_id,
    )

    session.add(organization_membership)
    session.commit()
    session.refresh(organization_membership)

    return CreateOrganizationMembershipResponse(
        id=organization_membership.id,
        role=organization_membership.role,
        organization_id=organization_membership.organization_id,
        user_id=organization_membership.user_id,
        created_at=organization_membership.created_at,
    )
