from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr, StringConstraints
from sqlalchemy.orm import Session

from ledgerlab.database import get_session
from ledgerlab.models import User

router = APIRouter()


class CreateUserRequest(BaseModel):
    name: Annotated[
        str,
        StringConstraints(
            strip_whitespace=True,
            min_length=1,
        ),
    ]
    email: EmailStr


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
    user = User(name=request.name, email=request.email)

    session.add(user)
    session.commit()
    session.refresh(user)

    return CreateUserResponse(
        id=user.id, name=user.name, email=user.email, created_at=user.created_at
    )
