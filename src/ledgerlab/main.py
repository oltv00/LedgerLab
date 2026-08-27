from typing import Annotated

from fastapi import Depends, FastAPI
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ledgerlab.database import get_session
from ledgerlab.models import Organization

app = FastAPI()

class CreateOrganizationRequest(BaseModel):
    name: str

@app.get('/health')
def health() -> dict[str, str]:
    return {'status': 'ok'}

@app.post('/organizations', status_code=201)
def create_organization(
    request: CreateOrganizationRequest,
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, str]:
    organization = Organization(name=request.name)

    session.add(organization)
    session.commit()

    return {'name': organization.name}
