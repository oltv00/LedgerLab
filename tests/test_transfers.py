from collections.abc import Callable
from datetime import datetime
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from psycopg.errors import CheckViolation, ForeignKeyViolation
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from ledgerlab.database import session_factory
from ledgerlab.main import app
from ledgerlab.models import Account, LedgerEntry, Transfer

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


@pytest.fixture
def account_id_with_custom_organization_id() -> Callable[[str, UUID], UUID]:
    def make_account_id(
        account_name: str,
        organization_id: UUID,
    ) -> UUID:
        with session_factory() as session:
            account = Account(
                id=uuid4(),
                name=account_name,
                organization_id=organization_id,
            )
            session.add(account)
            session.commit()
            session.refresh(account)

        return account.id

    return make_account_id


@pytest.fixture
def transfer_id(
    organization_id: UUID,
    source_account_id: UUID,
    destination_account_id: UUID,
) -> UUID:
    with session_factory() as session:
        transfer_id = uuid4()
        transfer = Transfer(
            id=transfer_id,
            organization_id=organization_id,
            source_account_id=source_account_id,
            destination_account_id=destination_account_id,
            amount_minor=1000,
        )
        session.add(transfer)
        session.flush()

        ledger_entry_source = LedgerEntry(
            id=uuid4(),
            transfer_id=transfer_id,
            account_id=source_account_id,
            amount_minor=-1000,
        )

        ledger_entry_destination = LedgerEntry(
            id=uuid4(),
            transfer_id=transfer_id,
            account_id=destination_account_id,
            amount_minor=1000,
        )

        session.add_all([ledger_entry_source, ledger_entry_destination])
        session.commit()
    return transfer_id


def test_transfers_operator_create_transfer(
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


def test_transfers_admin_create_transfer(
    admin_access_token_headers: dict[str, str],
    organization_id: UUID,
    source_account_id: UUID,
    destination_account_id: UUID,
) -> None:
    response = client.post(
        f"/organizations/{organization_id}/transfers",
        headers=admin_access_token_headers,
        json={
            "source_account_id": str(source_account_id),
            "destination_account_id": str(destination_account_id),
            "amount_minor": 1000,
        },
    )

    assert response.status_code == 201


def test_transfers_rejects_no_access_token(
    organization_id: UUID,
    source_account_id: UUID,
    destination_account_id: UUID,
) -> None:
    response = client.post(
        f"/organizations/{organization_id}/transfers",
        json={
            "source_account_id": str(source_account_id),
            "destination_account_id": str(destination_account_id),
            "amount_minor": 1000,
        },
    )

    assert response.status_code == 401


def test_transfers_rejects_operator_from_another_organization(
    operator_access_token_headers_with_custom_organization_id: Callable[
        [UUID], dict[str, str]
    ],
    create_organization_id: Callable[[str], UUID],
    source_account_id: UUID,
    destination_account_id: UUID,
    organization_id: UUID,
) -> None:
    new_organization_id = create_organization_id("new_organization_name")
    headers = operator_access_token_headers_with_custom_organization_id(
        new_organization_id
    )
    response = client.post(
        f"/organizations/{organization_id}/transfers",
        headers=headers,
        json={
            "source_account_id": str(source_account_id),
            "destination_account_id": str(destination_account_id),
            "amount_minor": 1000,
        },
    )

    assert response.status_code == 403


def test_transfers_rejects_source_account_id_outside_target_organization(
    operator_access_token_headers: dict[str, str],
    destination_account_id: UUID,
    organization_id: UUID,
    create_organization_id: Callable[[str], UUID],
    account_id_with_custom_organization_id: Callable[[str, UUID], UUID],
) -> None:
    new_organization_id = create_organization_id("new_organization_name")
    source_account_id = account_id_with_custom_organization_id(
        "source_account_name", new_organization_id
    )
    response = client.post(
        f"/organizations/{organization_id}/transfers",
        headers=operator_access_token_headers,
        json={
            "source_account_id": str(source_account_id),
            "destination_account_id": str(destination_account_id),
            "amount_minor": 1000,
        },
    )

    assert response.status_code == 403


def test_transfers_rejects_destination_account_id_outside_target_organization(
    operator_access_token_headers: dict[str, str],
    source_account_id: UUID,
    organization_id: UUID,
    create_organization_id: Callable[[str], UUID],
    account_id_with_custom_organization_id: Callable[[str, UUID], UUID],
) -> None:
    new_organization_id = create_organization_id("new_organization_name")
    destination_account_id = account_id_with_custom_organization_id(
        "destination_account_name", new_organization_id
    )
    response = client.post(
        f"/organizations/{organization_id}/transfers",
        headers=operator_access_token_headers,
        json={
            "source_account_id": str(source_account_id),
            "destination_account_id": str(destination_account_id),
            "amount_minor": 1000,
        },
    )

    assert response.status_code == 403


def test_transfers_rejects_equal_accounts_id(
    operator_access_token_headers: dict[str, str],
    source_account_id: UUID,
    organization_id: UUID,
) -> None:
    response = client.post(
        f"/organizations/{organization_id}/transfers",
        headers=operator_access_token_headers,
        json={
            "source_account_id": str(source_account_id),
            "destination_account_id": str(source_account_id),
            "amount_minor": 1000,
        },
    )

    assert response.status_code == 422


def test_transfers_rejects_unknown_account_id(
    operator_access_token_headers: dict[str, str],
    organization_id: UUID,
    source_account_id: UUID,
) -> None:
    response = client.post(
        f"/organizations/{organization_id}/transfers",
        headers=operator_access_token_headers,
        json={
            "source_account_id": str(source_account_id),
            "destination_account_id": str(uuid4()),
            "amount_minor": 1000,
        },
    )

    assert response.status_code == 403


def test_transfers_rejects_amount_minor_equal_zero(
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
            "amount_minor": 0,
        },
    )
    assert response.status_code == 422


def test_transfers_rejects_amount_minor_less_than_zero(
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
            "amount_minor": -1,
        },
    )
    assert response.status_code == 422


@pytest.mark.parametrize(
    "amount_minor",
    [
        "1000",
        1000.0,
        True,
    ],
)
def test_transfers_rejects_non_integer_amount_minor_value(
    amount_minor: object,
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
            "amount_minor": amount_minor,
        },
    )
    assert response.status_code == 422


def test_transfers_database_rejects_amount_minor_equal_zero(
    organization_id: UUID,
    source_account_id: UUID,
    destination_account_id: UUID,
) -> None:
    with session_factory() as session:
        transfer = Transfer(
            id=uuid4(),
            organization_id=organization_id,
            source_account_id=source_account_id,
            destination_account_id=destination_account_id,
            amount_minor=0,
        )
        session.add(transfer)

        with pytest.raises(IntegrityError) as exc_info:
            session.commit()

        error = exc_info.value
        assert isinstance(error.orig, CheckViolation)
        assert error.orig.diag.constraint_name == "ck_transfers_amount_minor_positive"


def test_transfers_database_rejects_equal_accounts_id(
    organization_id: UUID,
    source_account_id: UUID,
) -> None:
    with session_factory() as session:
        transfer = Transfer(
            id=uuid4(),
            organization_id=organization_id,
            source_account_id=source_account_id,
            destination_account_id=source_account_id,
            amount_minor=1000,
        )
        session.add(transfer)

        with pytest.raises(IntegrityError) as exc_info:
            session.commit()

        error = exc_info.value
        assert isinstance(error.orig, CheckViolation)
        assert (
            error.orig.diag.constraint_name
            == "ck_transfers_source_account_id_not_equal_destination_account_id"
        )


def test_transfers_database_rejects_source_account_id_outside_organization(
    organization_id: UUID,
    destination_account_id: UUID,
    create_organization_id: Callable[[str], UUID],
    account_id_with_custom_organization_id: Callable[[str, UUID], UUID],
) -> None:
    new_organization_id = create_organization_id("new_organization_name")
    source_account_id = account_id_with_custom_organization_id(
        "source_account_name",
        new_organization_id,
    )
    with session_factory() as session:
        transfer = Transfer(
            id=uuid4(),
            organization_id=organization_id,
            source_account_id=source_account_id,
            destination_account_id=destination_account_id,
            amount_minor=1000,
        )
        session.add(transfer)

        with pytest.raises(IntegrityError) as exc_info:
            session.commit()

        error = exc_info.value
        assert isinstance(error.orig, ForeignKeyViolation)
        assert (
            error.orig.diag.constraint_name
            == "fk_transfers_source_account_belongs_organization"
        )


def test_transfers_database_rejects_destination_account_id_outside_organization(
    organization_id: UUID,
    source_account_id: UUID,
    create_organization_id: Callable[[str], UUID],
    account_id_with_custom_organization_id: Callable[[str, UUID], UUID],
) -> None:
    new_organization_id = create_organization_id("new_organization_name")
    destination_account_id = account_id_with_custom_organization_id(
        "destination_account_name",
        new_organization_id,
    )
    with session_factory() as session:
        transfer = Transfer(
            id=uuid4(),
            organization_id=organization_id,
            source_account_id=source_account_id,
            destination_account_id=destination_account_id,
            amount_minor=1000,
        )
        session.add(transfer)

        with pytest.raises(IntegrityError) as exc_info:
            session.commit()

        error = exc_info.value
        assert isinstance(error.orig, ForeignKeyViolation)
        assert (
            error.orig.diag.constraint_name
            == "fk_transfers_destination_account_belongs_organization"
        )


def test_transfers_database_rejects_ledger_entry_update(
    organization_id: UUID,
    operator_access_token_headers: dict[str, str],
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

    transfer_id = response.json()["id"]
    with session_factory() as session:
        ledger_entry = session.execute(
            select(LedgerEntry).where(
                LedgerEntry.transfer_id == transfer_id,
            )
        ).scalar()

        assert ledger_entry is not None

        with pytest.raises(IntegrityError) as exception_info:
            session.execute(
                text(
                    "UPDATE ledger_entries "
                    "SET amount_minor = :amount_minor "
                    "WHERE id = :ledger_entry_id"
                ),
                {
                    "amount_minor": 999,
                    "ledger_entry_id": ledger_entry.id,
                },
            )

        error = exception_info.value
        assert isinstance(error.orig, CheckViolation)
        assert error.orig.diag.constraint_name == "ck_ledger_entries_immutable"


def test_transfers_database_rejects_ledger_entry_delete(
    organization_id: UUID,
    operator_access_token_headers: dict[str, str],
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

    transfer_id = response.json()["id"]
    with session_factory() as session:
        ledger_entry = session.execute(
            select(LedgerEntry).where(
                LedgerEntry.transfer_id == transfer_id,
            )
        ).scalar()

        assert ledger_entry is not None

        with pytest.raises(IntegrityError) as exception_info:
            session.execute(
                text("DELETE FROM ledger_entries WHERE id = :ledger_entry_id"),
                {
                    "ledger_entry_id": ledger_entry.id,
                },
            )

        error = exception_info.value
        assert isinstance(error.orig, CheckViolation)
        assert error.orig.diag.constraint_name == "ck_ledger_entries_immutable"


def test_transfers_database_rejects_transfer_without_ledger_entries(
    organization_id: UUID,
    source_account_id: UUID,
    destination_account_id: UUID,
) -> None:
    with session_factory() as session:
        transfer_id = uuid4()
        transfer = Transfer(
            id=transfer_id,
            organization_id=organization_id,
            source_account_id=source_account_id,
            destination_account_id=destination_account_id,
            amount_minor=1000,
        )
        session.add(transfer)

        with pytest.raises(IntegrityError) as exception_info:
            session.commit()

    error = exception_info.value
    assert isinstance(error.orig, CheckViolation)
    assert error.orig.diag.constraint_name == "ck_transfers_exactly_two_ledger_entries"

    with session_factory() as session:
        persisted_transfer = session.execute(
            select(Transfer).where(
                Transfer.id == transfer_id,
            )
        ).scalar_one_or_none()

    assert persisted_transfer is None


def test_transfers_database_rejects_third_ledger_entry(
    organization_id: UUID,
    operator_access_token_headers: dict[str, str],
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

    with session_factory() as session:
        transfer_id = UUID(response.json()["id"])
        ledger_entry = LedgerEntry(
            id=uuid4(),
            transfer_id=transfer_id,
            account_id=source_account_id,
            amount_minor=1,
        )
        session.add(ledger_entry)

        with pytest.raises(IntegrityError) as exception_error:
            session.commit()

    error = exception_error.value
    assert isinstance(error.orig, CheckViolation)
    assert error.orig.diag.constraint_name == "ck_transfers_exactly_two_ledger_entries"

    with session_factory() as session:
        ledger_entries = (
            session.execute(
                select(LedgerEntry).where(
                    LedgerEntry.transfer_id == transfer_id,
                )
            )
            .scalars()
            .all()
        )

    assert len(ledger_entries) == 2


def test_transfers_database_rejects_pair_amounts_not_matching_transfer(
    organization_id: UUID,
    source_account_id: UUID,
    destination_account_id: UUID,
) -> None:
    with session_factory() as session:
        transfer_id = uuid4()
        transfer = Transfer(
            id=transfer_id,
            organization_id=organization_id,
            source_account_id=source_account_id,
            destination_account_id=destination_account_id,
            amount_minor=1000,
        )
        session.add(transfer)
        session.flush()

        ledger_entry_source = LedgerEntry(
            id=uuid4(),
            transfer_id=transfer_id,
            account_id=source_account_id,
            amount_minor=-999,
        )

        ledger_entry_destination = LedgerEntry(
            id=uuid4(),
            transfer_id=transfer_id,
            account_id=destination_account_id,
            amount_minor=999,
        )

        session.add_all([ledger_entry_source, ledger_entry_destination])

        with pytest.raises(IntegrityError) as exception_info:
            session.commit()

    error = exception_info.value
    assert isinstance(error.orig, CheckViolation)
    assert error.orig.diag.constraint_name == "ck_ledger_entries_match_transfer_amounts"

    with session_factory() as session:
        persisted_transfer = session.get(Transfer, transfer_id)
        assert persisted_transfer is None

        persisted_ledger_entries = (
            session.execute(
                select(LedgerEntry).where(
                    LedgerEntry.transfer_id == transfer_id,
                )
            )
            .scalars()
            .all()
        )

        assert len(persisted_ledger_entries) == 0


def test_transfers_database_rejects_transfer_amount_update(
    transfer_id: UUID,
) -> None:
    with session_factory() as session, pytest.raises(IntegrityError) as exception_info:
        session.execute(
            text(
                "UPDATE transfers "
                "SET amount_minor = :amount_minor "
                "WHERE id = :transfer_id"
            ),
            {
                "amount_minor": 999,
                "transfer_id": transfer_id,
            },
        )

    error = exception_info.value
    assert isinstance(error.orig, CheckViolation)
    assert error.orig.diag.constraint_name == "ck_transfers_immutable"


def test_transfers_database_rejects_transfer_delete(
    transfer_id: UUID,
) -> None:
    with session_factory() as session, pytest.raises(IntegrityError) as exception_info:
        session.execute(
            text("DELETE FROM transfers WHERE id = :transfer_id"),
            {
                "transfer_id": transfer_id,
            },
        )

    error = exception_info.value
    assert isinstance(error.orig, CheckViolation)
    assert error.orig.diag.constraint_name == "ck_transfers_immutable"
