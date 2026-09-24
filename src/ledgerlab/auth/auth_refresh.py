import os
from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID, uuid4

import jwt
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ledgerlab.database import get_session
from ledgerlab.models import RefreshToken

router = APIRouter()


class AuthRefreshRequest(BaseModel):
    refresh_token: str | None = None


class AuthRefreshResponse(BaseModel):
    access_token: str
    refresh_token: str


def get_refresh_token(
    request: AuthRefreshRequest,
    database_session: Annotated[Session, Depends(get_session)],
) -> RefreshToken:

    if request.refresh_token is None:
        raise HTTPException(
            status_code=401,
            detail="Credentials are invalid",
        )

    try:
        payload = jwt.decode(
            jwt=request.refresh_token,
            key=os.environ["JWT_SECRET"],
            algorithms=["HS256"],
            options={"require": ["sub", "exp", "jti", "typ"]},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail="Credentials are invalid",
        ) from None

    if payload["typ"] != "refresh":
        raise HTTPException(
            status_code=401,
            detail="Credentials are invalid",
        )

    try:
        payload_sub_uuid = UUID(payload["sub"])
        payload_jti_uuid = UUID(payload["jti"])
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(
            status_code=401,
            detail="Credentials are invalid",
        ) from None

    refresh_token = database_session.execute(
        select(RefreshToken)
        .where(
            RefreshToken.jti == payload_jti_uuid,
        )
        .with_for_update()
    ).scalar_one_or_none()

    if refresh_token is None:
        raise HTTPException(
            status_code=401,
            detail="Credentials are invalid",
        )

    if refresh_token.user_id != payload_sub_uuid:
        raise HTTPException(
            status_code=401,
            detail="Credentials are invalid",
        )

    if refresh_token.revoked_at is not None:
        raise HTTPException(
            status_code=401,
            detail="Credentials are invalid",
        )

    if refresh_token.expires_at <= datetime.now(UTC):
        raise HTTPException(
            status_code=401,
            detail="Credentials are invalid",
        )

    return refresh_token


@router.post(
    "/auth/refresh",
    status_code=200,
    response_model=AuthRefreshResponse,
)
def auth_refresh(
    database_session: Annotated[Session, Depends(get_session)],
    current_refresh_token: Annotated[RefreshToken, Depends(get_refresh_token)],
) -> AuthRefreshResponse:

    current_refresh_token.revoked_at = datetime.now(UTC)
    database_session.add(current_refresh_token)

    new_jti = uuid4()
    new_refresh_token_expires_at = (datetime.now(UTC) + timedelta(days=7)).replace(
        microsecond=0
    )
    new_refresh_token = RefreshToken(
        jti=new_jti,
        user_id=current_refresh_token.user_id,
        expires_at=new_refresh_token_expires_at,
    )
    database_session.add(new_refresh_token)

    access_token_expires_at = datetime.now(UTC) + timedelta(minutes=15)
    access_token_payload = {
        "sub": str(current_refresh_token.user_id),
        "exp": access_token_expires_at,
        "typ": "access",
    }
    access_token = jwt.encode(
        payload=access_token_payload,
        key=os.environ["JWT_SECRET"],
        algorithm="HS256",
    )

    refresh_token_payload = {
        "sub": str(current_refresh_token.user_id),
        "exp": new_refresh_token_expires_at,
        "typ": "refresh",
        "jti": str(new_jti),
    }
    refresh_token = jwt.encode(
        payload=refresh_token_payload,
        key=os.environ["JWT_SECRET"],
        algorithm="HS256",
    )

    database_session.commit()

    return AuthRefreshResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )
