from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ledgerlab.auth.auth_refresh import get_refresh_token
from ledgerlab.database import get_session
from ledgerlab.models import RefreshToken

router = APIRouter()


@router.post(
    "/auth/logout",
    status_code=204,
)
def logout(
    current_refresh_token: Annotated[RefreshToken, Depends(get_refresh_token)],
    database_session: Annotated[Session, Depends(get_session)],
) -> None:
    current_refresh_token.revoked_at = datetime.now(UTC)
    database_session.add(current_refresh_token)
    database_session.commit()
