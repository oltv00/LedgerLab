import os
from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import uuid4

import jwt
from fastapi import APIRouter, Depends, HTTPException
from pwdlib import PasswordHash
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from ledgerlab.database import get_session
from ledgerlab.models import User

router = APIRouter()
password_hashing = PasswordHash.recommended()


class CreateLoginRequest(BaseModel):
    email: EmailStr
    password: str


class CreateLoginResponse(BaseModel):
    access_token: str
    refresh_token: str


@router.post(
    "/auth/login",
    status_code=200,
    response_model=CreateLoginResponse,
)
def create_login(
    request: CreateLoginRequest,
    session: Annotated[Session, Depends(get_session)],
) -> CreateLoginResponse:
    user = (
        session.execute(
            select(User).where(
                User.email == request.email,
            )
        )
    ).scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Credentials are invalid",
        )

    if user.password_hash is None:
        raise HTTPException(
            status_code=401,
            detail="Credentials are invalid",
        )

    if not password_hashing.verify(
        request.password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=401,
            detail="Credentials are invalid",
        )

    expires_at = datetime.now(UTC) + timedelta(minutes=15)
    access_claims = {
        "sub": str(user.id),
        "exp": expires_at,
        "typ": "access",
    }
    access_token = jwt.encode(
        access_claims,
        key=os.environ["JWT_SECRET"],
        algorithm="HS256",
    )

    expires_at = datetime.now(UTC) + timedelta(days=7)
    refresh_claims = {
        "sub": str(user.id),
        "exp": expires_at,
        "typ": "refresh",
        "jti": str(uuid4()),
    }
    refresh_token = jwt.encode(
        refresh_claims,
        key=os.environ["JWT_SECRET"],
        algorithm="HS256",
    )

    return CreateLoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )
