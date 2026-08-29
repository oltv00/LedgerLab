from datetime import datetime
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends
from pydantic import BaseModel, StringConstraints
from sqlalchemy.orm import Session

from ledgerlab.database import get_session

router = APIRouter()

class CreateUserRequest(BaseModel):
    name: Annotated[
        str,
        StringConstraints(
            strip_whitespace=True,
            min_length=1,
        ),
    ]
    email: Annotated[
        str,
        StringConstraints(
            strip_whitespace=True,
            min_length=1,
        ),
        # StringConstraints(pattern="/^[\\w\\-\\.]+@([\\w-]+\\.)+[\\w-]{2,}$"),
    ]

class CreateUserResponse(BaseModel):
    id: UUID
    name: str
    email: str
    created_at: datetime

@router.post(
    "/users",
    status_code=201,
    response_model=CreateUserResponse,
)
def create_user(
    request: CreateUserRequest,
    session: Annotated[Session, Depends(get_session)],
) -> CreateUserResponse:
    return CreateUserResponse(
        id=uuid4(),
        name=request.name,
        email=request.email,
        created_at=datetime(1, 1, 1)
    )
