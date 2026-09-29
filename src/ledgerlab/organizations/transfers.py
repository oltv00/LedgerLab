from datetime import datetime
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ledgerlab.current_user import get_authenticated_user
from ledgerlab.database import get_session
from ledgerlab.models import (
    Account,
    LedgerEntry,
    OrganizationMembership,
    Transfer,
    User,
)

router = APIRouter()


class TransferRequest(BaseModel):
    source_account_id: UUID
    destination_account_id: UUID
    amount_minor: Annotated[int, Field(gt=0)]


class TransferResponse(BaseModel):
    id: UUID
    organization_id: UUID
    source_account_id: UUID
    destination_account_id: UUID
    amount_minor: int
    created_at: datetime


@router.post(
    "/organizations/{organization_id}/transfers",
    status_code=201,
    response_model=TransferResponse,
)
def create_transfer(
    database_session: Annotated[Session, Depends(get_session)],
    current_user: Annotated[User, Depends(get_authenticated_user)],
    request: TransferRequest,
    organization_id: UUID,
) -> TransferResponse:

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

    if membership.role not in ["admin", "operator"]:
        raise HTTPException(
            status_code=403,
            detail="Request is forbidden",
        )

    if request.source_account_id == request.destination_account_id:
        raise HTTPException(
            status_code=422,
            detail="Source and destination accounts must differ",
        )

    source_account = database_session.get(Account, request.source_account_id)
    if source_account is None:
        raise HTTPException(
            status_code=403,
            detail="Request is forbidden",
        )

    destination_account = database_session.get(Account, request.destination_account_id)
    if destination_account is None:
        raise HTTPException(
            status_code=403,
            detail="Request is forbidden",
        )

    if source_account.organization_id != destination_account.organization_id:
        raise HTTPException(
            status_code=403,
            detail="Request is forbidden",
        )

    if membership.organization_id != source_account.organization_id:
        raise HTTPException(
            status_code=403,
            detail="Request is forbidden",
        )

    if membership.organization_id != destination_account.organization_id:
        raise HTTPException(
            status_code=403,
            detail="Request is forbidden",
        )

    transfer_id = uuid4()
    transfer = Transfer(
        id=transfer_id,
        organization_id=organization_id,
        source_account_id=request.source_account_id,
        destination_account_id=request.destination_account_id,
        amount_minor=request.amount_minor,
    )
    database_session.add(transfer)
    database_session.flush()

    ledger_source_entry = LedgerEntry(
        id=uuid4(),
        transfer_id=transfer_id,
        account_id=request.source_account_id,
        amount_minor=-request.amount_minor,
    )

    ledger_destination_entry = LedgerEntry(
        id=uuid4(),
        transfer_id=transfer_id,
        account_id=request.destination_account_id,
        amount_minor=request.amount_minor,
    )

    database_session.add_all(
        [ledger_source_entry, ledger_destination_entry],
    )
    database_session.commit()
    database_session.refresh(transfer)

    return TransferResponse(
        id=transfer.id,
        organization_id=transfer.organization_id,
        source_account_id=transfer.source_account_id,
        destination_account_id=transfer.destination_account_id,
        amount_minor=transfer.amount_minor,
        created_at=transfer.created_at,
    )
