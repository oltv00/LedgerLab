import os
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ledgerlab.database import get_session
from ledgerlab.models import User

router = APIRouter()
bearer_security = HTTPBearer(auto_error=False)


class CurrentUserResponse(BaseModel):
    id: UUID
    name: str
    email: str


def get_authenticated_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_security),
    ],
    session: Annotated[Session, Depends(get_session)],
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Credentials are invalid",
        )

    access_token = credentials.credentials
    try:
        payload = jwt.decode(
            jwt=access_token,
            key=os.environ["JWT_SECRET"],
            algorithms=["HS256"],
            options={"require": ["sub", "exp"]},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail="Credentials are invalid",
        ) from None

    try:
        user_id = UUID(payload["sub"])
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(
            status_code=401,
            detail="Credentials are invalid",
        ) from None

    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Credentials are invalid",
        )
    return user


@router.get(
    "/auth/me",
    status_code=200,
    response_model=CurrentUserResponse,
)
def get_current_user(
    current_user: Annotated[User, Depends(get_authenticated_user)],
) -> CurrentUserResponse:
    return CurrentUserResponse(
        id=current_user.id,
        name=current_user.name,
        email=current_user.email,
    )
