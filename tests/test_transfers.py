from datetime import datetime
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from ledgerlab.database import session_factory
from ledgerlab.main import app
from ledgerlab.models import Account

client = TestClient(app=app)


@pytest.fixture
def source_account_id(
    organization_id: UUID,
) -> UUID:
    with session_factory() as session:
        account = Account(
            id=uuid4(),
            name="source_account_name",
            organization_id=organization_id,
        )
        session.add(account)
        session.commit()
        session.refresh(account)

    return account.id


@pytest.fixture
def destination_account_id(
    organization_id: UUID,
) -> UUID:
    with session_factory() as session:
        account = Account(
            id=uuid4(),
            name="destination_account_name",
            organization_id=organization_id,
        )
        session.add(account)
        session.commit()
        session.refresh(account)

    return account.id


def test_transfers_create_transfer(
    operator_access_token_headers: dict[str, str],
    organization_id: UUID,
    source_account_id: UUID,
    destination_account_id: UUID,
) -> None:
    response = client.post(
        f"/organizations/{organization_id}/transfers",
        headers=operator_access_token_headers,
        json={
            "source_account_id": str(source_account_id),
            "destination_account_id": str(destination_account_id),
            "amount_minor": 1000,
        },
    )

    assert response.status_code == 201
    response_body = response.json()

    transfer_id = UUID(response_body["id"])
    assert transfer_id is not None
    assert UUID(response_body["organization_id"]) == organization_id
    assert UUID(response_body["source_account_id"]) == source_account_id
    assert UUID(response_body["destination_account_id"]) == destination_account_id
    assert response_body["amount_minor"] == 1000

    created_at = response_body["created_at"]
    assert "T" in created_at
    assert datetime.fromisoformat(created_at).tzinfo is not None

    with session_factory() as session:
        database_transfer = (
            session.execute(
                text(
                    "SELECT id, organization_id, source_account_id, "
                    "destination_account_id, amount_minor, created_at "
                    "FROM transfers "
                    "WHERE id = :transfer_id"
                ),
                {
                    "transfer_id": transfer_id,
                },
            )
            .mappings()
            .one_or_none()
        )

        assert database_transfer is not None
        assert database_transfer["id"] == transfer_id
        assert database_transfer["organization_id"] == organization_id
        assert database_transfer["source_account_id"] == source_account_id
        assert database_transfer["destination_account_id"] == destination_account_id
        assert database_transfer["amount_minor"] == 1000
        assert database_transfer["created_at"].tzinfo is not None

        database_ledger_rows = session.execute(
            text(
                "SELECT COUNT(*) FROM ledger_entries WHERE transfer_id = :transfer_id"
            ),
            {
                "transfer_id": transfer_id,
            },
        ).scalar_one_or_none()

        assert database_ledger_rows == 2

        database_ledger_source = (
            session.execute(
                text(
                    "SELECT id, transfer_id, account_id, amount_minor, created_at "
                    "FROM ledger_entries "
                    "WHERE transfer_id = :transfer_id "
                    "AND account_id = :account_id"
                ),
                {
                    "transfer_id": transfer_id,
                    "account_id": source_account_id,
                },
            )
            .mappings()
            .one_or_none()
        )

        database_ledger_destination = (
            session.execute(
                text(
                    "SELECT id, transfer_id, account_id, amount_minor, created_at "
                    "FROM ledger_entries "
                    "WHERE transfer_id = :transfer_id "
                    "AND account_id = :account_id"
                ),
                {
                    "transfer_id": transfer_id,
                    "account_id": destination_account_id,
                },
            )
            .mappings()
            .one_or_none()
        )

        assert database_ledger_source is not None
        assert database_ledger_destination is not None

        assert (
            database_ledger_source["transfer_id"]
            == database_ledger_destination["transfer_id"]
        )

        assert database_ledger_source["account_id"] == source_account_id
        assert database_ledger_destination["account_id"] == destination_account_id

        assert database_ledger_source["amount_minor"] == -1000
        assert database_ledger_destination["amount_minor"] == 1000

        assert (
            database_ledger_source["amount_minor"]
            + database_ledger_destination["amount_minor"]
            == 0
        )

        assert (
            database_ledger_source["created_at"]
            == database_ledger_destination["created_at"]
        )
        assert database_ledger_source["created_at"].tzinfo is not None
        assert database_ledger_destination["created_at"].tzinfo is not None
