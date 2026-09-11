from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pwdlib import PasswordHash
from pydantic import BaseModel, EmailStr, StringConstraints
from sqlalchemy import select
from sqlalchemy.orm import Session

from ledgerlab.database import get_session
from ledgerlab.models import User

router = APIRouter()
password_hashing = PasswordHash.recommended()


class CreateRegisterRequest(BaseModel):
    name: Annotated[
        str,
        StringConstraints(
            strip_whitespace=True,
            min_length=1,
        ),
    ]
    email: EmailStr
    password: Annotated[
        str,
        StringConstraints(
            min_length=12,
            max_length=128,
        ),
    ]


class CreateRegisterResponse(BaseModel):
    id: UUID
    name: str
    email: str
    created_at: datetime


@router.post(
    "/auth/register",
    status_code=201,
    response_model=CreateRegisterResponse,
)
def create_register(
    request: CreateRegisterRequest,
    session: Annotated[Session, Depends(get_session)],
) -> CreateRegisterResponse:
    existing_user = (
        session.execute(
            select(User).where(
                User.email == request.email,
            )
        )
    ).scalar_one_or_none()
    if existing_user is not None:
        raise HTTPException(
            status_code=409,
            detail="User with this email already exists",
        )

    user = User(
        name=request.name,
        email=request.email,
    )

    user.password_hash = password_hashing.hash(
        password=request.password,
        salt=None,
    )

    session.add(user)
    session.commit()
    session.refresh(user)

    return CreateRegisterResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        created_at=user.created_at,
    )
