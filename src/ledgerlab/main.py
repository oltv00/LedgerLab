from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ledgerlab.database import get_session
from ledgerlab.models import Organization

app = FastAPI()

class CreateOrganizationRequest(BaseModel):
    name: str

class CreateOrganizationResponse(BaseModel):
    id: UUID
    name: str
    created_at: datetime

@app.get('/health')
def health() -> dict[str, str]:
    return {'status': 'ok'}

@app.post(
    '/organizations',
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
