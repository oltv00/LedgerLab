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


class GetOrganizationResponse(BaseModel):
    id: UUID
    name: str
    created_at: datetime


@router.get(
    "/organizations/{organization_id}",
    status_code=200,
    response_model=GetOrganizationResponse,
)
def get_organization(
    organization_id: UUID,
    current_user: Annotated[User, Depends(get_authenticated_user)],
    session: Annotated[Session, Depends(get_session)],
) -> GetOrganizationResponse:
    membership = (
        session.execute(
            select(OrganizationMembership).where(
                OrganizationMembership.user_id == current_user.id,
                OrganizationMembership.organization_id == organization_id,
            )
        )
    ).scalar_one_or_none()
    if membership is None:
        raise HTTPException(
            status_code=403,
            detail="403 Forbidden",
        )

    organization = session.get(Organization, organization_id)
    if organization is None:
        raise HTTPException(
            status_code=404,
            detail="404 Not Found",
        )

    return GetOrganizationResponse(
        id=organization.id,
        name=organization.name,
        created_at=organization.created_at,
    )
