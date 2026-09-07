from collections.abc import Generator
from datetime import datetime
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, text

from ledgerlab.database import session_factory
from ledgerlab.main import app
from ledgerlab.models import Organization, OrganizationMembership, User

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_memberships() -> Generator[None]:
    with session_factory() as session:
        session.execute(delete(OrganizationMembership))
        session.execute(delete(User))
        session.execute(delete(Organization))
        session.commit()

    yield

    with session_factory() as session:
        session.execute(delete(OrganizationMembership))
        session.execute(delete(User))
        session.execute(delete(Organization))
        session.commit()


def test_create_organization_membership_persists_membership() -> None:
    with session_factory() as session:
        organization = Organization(name="organization_name_value")
        user = User(name="user_name_value", email="email_value@domain.com")

        session.add_all([organization, user])
        session.commit()
        session.refresh(organization)
        session.refresh(user)

        organization_id = organization.id
        user_id = user.id

    response = client.post(
        f"/organizations/{organization_id}/memberships",
        json={"user_id": str(user_id)},
    )

    assert response.status_code == 201
    response_body = response.json()
    membership_id = response_body["id"]

    assert UUID(membership_id)
    assert UUID(response_body["organization_id"]) == organization_id
    assert UUID(response_body["user_id"]) == user_id
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
    assert persisted_membership["user_id"] == user_id
    assert persisted_membership["created_at"].tzinfo is not None


def test_create_organization_membership_rejects_unknown_organization() -> None:
    with session_factory() as session:
        user = User(name="user_name_value", email="email_value@domain.com")
        session.add(user)
        session.commit()
        session.refresh(user)

        user_id = user.id

    organization_id = UUID("12345678-1234-5678-1234-567812345678")

    response = client.post(
        f"/organizations/{organization_id}/memberships",
        json={"user_id": str(user_id)},
    )

    assert response.status_code == 404
