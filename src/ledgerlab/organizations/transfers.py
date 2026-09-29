from datetime import datetime
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ledgerlab.database import get_session
from ledgerlab.models import LedgerEntry, Transfer

router = APIRouter()


class TransferReuqest(BaseModel):
    source_account_id: UUID
    destination_account_id: UUID
    amount_minor: int


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
    request: TransferReuqest,
    organization_id: UUID,
) -> TransferResponse:
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
