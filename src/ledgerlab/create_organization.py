from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, StringConstraints
from sqlalchemy.orm import Session

from ledgerlab.database import get_session
from ledgerlab.models import Organization

router = APIRouter()


class CreateOrganizationRequest(BaseModel):
    name: Annotated[
        str,
        StringConstraints(
            strip_whitespace=True,
            min_length=1,
        ),
    ]


class CreateOrganizationResponse(BaseModel):
    id: UUID
    name: str
    created_at: datetime


@router.post(
    "/organizations",
    status_code=201,
    response_model=CreateOrganizationResponse,
)
def create_organization(
    request: CreateOrganizationRequest,
    session: Annotated[Session, Depends(get_session)],
) -> CreateOrganizationResponse:
    organization = Organization(name=request.name)

    session.add(organization)
    session.commit()
    session.refresh(organization)

    return CreateOrganizationResponse(
        id=organization.id,
        name=organization.name,
        created_at=organization.created_at,
    )
