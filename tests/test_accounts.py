from collections.abc import Callable
from datetime import datetime
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import text

from ledgerlab.database import session_factory
from ledgerlab.main import app

client = TestClient(app=app)


def test_accounts_create_account(
    admin_access_token_headers: dict[str, str],
    organization_id: UUID,
) -> None:
    account_name = "account_name_value"
    response = client.post(
        f"/organizations/{organization_id}/accounts",
        headers=admin_access_token_headers,
        json={"name": account_name},
    )

    assert response.status_code == 201

    response_body = response.json()
    account_id_uuid = UUID(response_body["id"])
    assert account_id_uuid is not None
    assert response_body["name"] == account_name
    assert UUID(response_body["organization_id"]) == organization_id

    created_at = response_body["created_at"]
    assert "T" in created_at
    assert datetime.fromisoformat(created_at).tzinfo is not None

    with session_factory() as session:
        database_account = (
            session.execute(
                text(
                    "SELECT id, name, organization_id, created_at "
                    "FROM accounts "
                    "WHERE id = :id"
                ),
                {
                    "id": account_id_uuid,
                },
            )
            .mappings()
            .one_or_none()
        )

    assert database_account is not None
    assert database_account["id"] == account_id_uuid
    assert database_account["name"] == account_name
    assert database_account["organization_id"] == organization_id
    assert database_account["created_at"].tzinfo is not None


def test_accounts_rejects_cross_tenant_admin_access(
    admin_access_token_headers: dict[str, str],
    create_organization_id: Callable[[str], UUID],
) -> None:
    new_organization_id = create_organization_id("new_organization_name")
    response = client.post(
        f"/organizations/{new_organization_id}/accounts",
        headers=admin_access_token_headers,
        json={
            "name": "name_value",
        },
    )
    assert response.status_code == 403


def test_accounts_rejects_operator(
    operator_access_token_headers: dict[str, str],
    organization_id: UUID,
) -> None:
    response = client.post(
        f"/organizations/{organization_id}/accounts",
        headers=operator_access_token_headers,
        json={
            "name": "name_value",
        },
    )
    assert response.status_code == 403


def test_accounts_rejects_without_access_token_headers(
    organization_id: UUID,
) -> None:
    response = client.post(
        f"/organizations/{organization_id}/accounts",
        json={
            "name": "name_value",
        },
    )
    assert response.status_code == 401


def test_accounts_rejects_empty_name(
    admin_access_token_headers: dict[str, str],
    organization_id: UUID,
) -> None:
    response = client.post(
        f"/organizations/{organization_id}/accounts",
        headers=admin_access_token_headers,
        json={
            "name": "",
        },
    )
    assert response.status_code == 422


def test_accounts_trim_account_name_whitespace(
    admin_access_token_headers: dict[str, str],
    organization_id: UUID,
) -> None:
    response = client.post(
        f"/organizations/{organization_id}/accounts",
        headers=admin_access_token_headers,
        json={
            "name": "   name_value   ",
        },
    )
    assert response.status_code == 201
    assert response.json()["name"] == "name_value"


def test_accounts_rejects_account_name_whitespace_only(
    admin_access_token_headers: dict[str, str],
    organization_id: UUID,
) -> None:
    response = client.post(
        f"/organizations/{organization_id}/accounts",
        headers=admin_access_token_headers,
        json={
            "name": "   ",
        },
    )
    assert response.status_code == 422


def test_accounts_reject_unknown_organization(
    admin_access_token_headers: dict[str, str],
) -> None:
    organization_id = UUID("12345678-1234-5678-1234-567812345678")
    response = client.post(
        f"/organizations/{organization_id}/accounts",
        headers=admin_access_token_headers,
        json={
            "name": "name_value",
        },
    )
    assert response.status_code == 403
