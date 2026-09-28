from collections.abc import Callable
from datetime import datetime
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text

from ledgerlab.database import session_factory
from ledgerlab.main import app
from ledgerlab.models import Organization, OrganizationMembership, User

client = TestClient(app)


@pytest.fixture
def new_user_id() -> UUID:
    with session_factory() as session:
        user = User(
            name="new_user_name_value",
            email="another_email_value@domain.com",
        )
        session.add(user)
        session.commit()
        session.refresh(user)
    return user.id


def test_create_organization_membership_persists_membership(
    admin_access_token_headers: dict[str, str],
    organization_id: UUID,
    new_user_id: UUID,
) -> None:
    response = client.post(
        f"/organizations/{organization_id}/memberships",
        headers=admin_access_token_headers,
        json={"user_id": str(new_user_id)},
    )

    assert response.status_code == 201
    response_body = response.json()
    membership_id = response_body["id"]

    assert UUID(membership_id)
    assert UUID(response_body["organization_id"]) == organization_id
    assert UUID(response_body["user_id"]) == new_user_id
    created_at = response_body["created_at"]
    assert "T" in created_at
    assert datetime.fromisoformat(created_at).tzinfo is not None

    with session_factory() as session:
        persisted_membership = (
            session.execute(
                text(
                    "SELECT id, organization_id, user_id, created_at FROM organization_memberships WHERE id=:id"
                ),
                {"id": membership_id},
            )
            .mappings()
            .one()
        )

    assert persisted_membership["id"] == UUID(response_body["id"])
    assert persisted_membership["organization_id"] == organization_id
    assert persisted_membership["user_id"] == new_user_id
    assert persisted_membership["created_at"].tzinfo is not None


def test_create_organization_membership_rejects_unknown_organization(
    admin_access_token_headers: dict[str, str],
    new_user_id: UUID,
) -> None:
    organization_id = UUID("12345678-1234-5678-1234-567812345678")

    response = client.post(
        f"/organizations/{organization_id}/memberships",
        headers=admin_access_token_headers,
        json={"user_id": str(new_user_id)},
    )

    assert response.status_code == 403


def test_create_organization_membership_rejects_unknown_user(
    admin_access_token_headers: dict[str, str],
    organization_id: UUID,
) -> None:
    user_id = UUID("12345678-1234-5678-1234-567812345678")

    response = client.post(
        f"/organizations/{organization_id}/memberships",
        headers=admin_access_token_headers,
        json={"user_id": str(user_id)},
    )

    assert response.status_code == 404


def test_create_organization_membership_rejects_duplicate_membership(
    admin_access_token_headers: dict[str, str],
    organization_id: UUID,
    new_user_id: UUID,
) -> None:
    with session_factory() as session:
        membership = OrganizationMembership(
            organization_id=organization_id, user_id=new_user_id
        )
        session.add(membership)
        session.commit()
        session.refresh(membership)

    response = client.post(
        f"/organizations/{organization_id}/memberships",
        headers=admin_access_token_headers,
        json={"user_id": str(new_user_id)},
    )

    assert response.status_code == 409

    with session_factory() as session:
        membership_count = session.execute(
            text(
                "SELECT COUNT(*) "
                "FROM organization_memberships "
                "WHERE organization_id = :organization_id "
                "AND user_id = :user_id"
            ),
            {
                "organization_id": organization_id,
                "user_id": new_user_id,
            },
        ).scalar_one()

        assert membership_count == 1


def test_create_organization_membership_assigns_operator_role(
    admin_access_token_headers: dict[str, str],
    organization_id: UUID,
    new_user_id: UUID,
) -> None:
    response = client.post(
        f"/organizations/{organization_id}/memberships",
        headers=admin_access_token_headers,
        json={"user_id": str(new_user_id)},
    )

    assert response.status_code == 201
    response_body = response.json()
    assert response_body["role"] == "operator"

    with session_factory() as session:
        existing_membership = (
            session.execute(
                select(OrganizationMembership).where(
                    OrganizationMembership.organization_id == organization_id,
                    OrganizationMembership.user_id == new_user_id,
                )
            )
        ).scalar_one()

        assert existing_membership.role == "operator"


def test_create_organization_membership_rejects_request_without_access_token() -> None:
    with session_factory() as session:
        user = User(name="user_name_value", email="email_value@domain.com")
        organization = Organization(name="organization_name_value")

        session.add_all([user, organization])
        session.commit()
        session.refresh(user)
        session.refresh(organization)

        organization_id = organization.id
        user_id = user.id

    response = client.post(
        f"/organizations/{organization_id}/memberships",
        json={"user_id": str(user_id)},
    )

    assert response.status_code == 401


def test_create_organization_membership_rejects_for_operator_role(
    operator_access_token_headers: dict[str, str],
    organization_id: UUID,
    new_user_id: UUID,
) -> None:
    response = client.post(
        f"/organizations/{organization_id}/memberships",
        headers=operator_access_token_headers,
        json={"user_id": str(new_user_id)},
    )

    assert response.status_code == 403

    with session_factory() as session:
        membership_count = session.execute(
            text(
                "SELECT COUNT(*) "
                "FROM organization_memberships "
                "WHERE organization_id = :organization_id "
                "AND user_id = :user_id"
            ),
            {
                "organization_id": organization_id,
                "user_id": new_user_id,
            },
        ).scalar_one()

        assert membership_count == 0


def test_create_organization_membership_rejects_for_admin_from_another_tenant(
    admin_access_token_headers: dict[str, str],
    create_organization_id: Callable[[str], UUID],
    new_user_id: UUID,
) -> None:
    target_organization_id = create_organization_id("new_organization")

    response = client.post(
        f"/organizations/{target_organization_id}/memberships",
        headers=admin_access_token_headers,
        json={"user_id": str(new_user_id)},
    )

    assert response.status_code == 403

    with session_factory() as session:
        membership_count = session.execute(
            text(
                "SELECT COUNT(*) "
                "FROM organization_memberships "
                "WHERE organization_id = :organization_id "
                "AND user_id = :user_id"
            ),
            {
                "organization_id": target_organization_id,
                "user_id": new_user_id,
            },
        ).scalar_one()

        assert membership_count == 0
