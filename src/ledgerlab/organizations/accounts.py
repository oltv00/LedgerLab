from datetime import datetime
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, StringConstraints
from sqlalchemy import select
from sqlalchemy.orm import Session

from ledgerlab.current_user import get_authenticated_user
from ledgerlab.database import get_session
from ledgerlab.models import Account, OrganizationMembership, User

router = APIRouter()


class AccountsRequest(BaseModel):
    name: Annotated[
        str,
        StringConstraints(
            min_length=1,
            strip_whitespace=True,
        ),
    ]


class AccountsResponse(BaseModel):
    id: UUID
    name: str
    organization_id: UUID
    created_at: datetime


@router.post(
    "/organizations/{organization_id}/accounts",
    status_code=201,
    response_model=AccountsResponse,
)
def create_account(
    database_session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_authenticated_user)],
    request: AccountsRequest,
    organization_id: UUID,
) -> AccountsResponse:
    membership = database_session.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.user_id == current_user.id,
        )
    ).scalar_one_or_none()

    if membership is None:
        raise HTTPException(
            status_code=403,
            detail="Request is forbidden",
        )

    if membership.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Request is forbidden",
        )

    account = Account(
        id=uuid4(),
        name=request.name,
        organization_id=organization_id,
    )
    database_session.add(account)
    database_session.commit()
    database_session.refresh(account)

    return AccountsResponse(
        id=account.id,
        name=account.name,
        organization_id=account.organization_id,
        created_at=account.created_at,
    )
