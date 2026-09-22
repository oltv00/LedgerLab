from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from ledgerlab.database import session_factory
from ledgerlab.main import app
from ledgerlab.models import Organization, OrganizationMembership, User

client = TestClient(app)


@pytest.fixture
def jwt_secret(monkeypatch: pytest.MonkeyPatch) -> str:
    secret = "04a58a7a876cdbeeee87ceaa6c9608caf60ec6a52eea4a950da39d6c50910bf2"
    monkeypatch.setenv("JWT_SECRET", secret)
    return secret


@pytest.fixture
def make_organization() -> Callable[[str], UUID]:
    def create(name: str) -> UUID:
        with session_factory() as session:
            organization = Organization(name=name)
            session.add(organization)
            session.commit()
            session.refresh(organization)
        return organization.id

    return create


@pytest.fixture
def organization_id(make_organization) -> UUID:
    return make_organization("organization_name_value")


@pytest.fixture
def authenticated_user_id() -> UUID:
    with session_factory() as session:
        user = User(
            name="user_name_value",
            email="email_value@domain.com",
        )
        session.add(user)
        session.commit()
        session.refresh(user)
    return user.id


@pytest.fixture
def authenticated_headers(
    jwt_secret: str,
    authenticated_user_id: UUID,
) -> dict[str, str]:
    exp = datetime.now(UTC) + timedelta(minutes=1)
    payload = {
        "sub": str(authenticated_user_id),
        "exp": exp,
    }
    access_token = jwt.encode(
        payload=payload,
        key=jwt_secret,
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def admin_authenticated_headers(
    organization_id: UUID,
    authenticated_user_id: UUID,
    authenticated_headers: dict[str, str],
) -> dict[str, str]:
    with session_factory() as session:
        membership = OrganizationMembership(
            organization_id=organization_id,
            user_id=authenticated_user_id,
            role="admin",
        )
        session.add(membership)
        session.commit()

    return authenticated_headers


def test_create_organization_returns_created_organization(
    authenticated_headers: dict[str, str],
) -> None:
    response = client.post(
        "/organizations",
        headers=authenticated_headers,
        json={"name": "Acme Operations"},
    )

    assert response.status_code == 201
    response_body = response.json()

    assert response_body["name"] == "Acme Operations"
    assert UUID(response_body["id"])

    created_at = response_body["created_at"]
    assert "T" in created_at
    assert datetime.fromisoformat(created_at).tzinfo is not None


def test_create_organization_rejects_whitespace_only_name(
    authenticated_headers: dict[str, str],
) -> None:
    response = client.post(
        "/organizations",
        headers=authenticated_headers,
        json={"name": "    "},
    )

    assert response.status_code == 422


def test_create_organization_trims_surrounding_whitespace(
    authenticated_headers: dict[str, str],
) -> None:
    response = client.post(
        "/organizations",
        headers=authenticated_headers,
        json={"name": "   Acme Operations   "},
    )

    assert response.status_code == 201
    assert response.json()["name"] == "Acme Operations"


def test_create_organization_persists_organization(
    authenticated_headers: dict[str, str],
) -> None:
    name = "organization_name"
    response = client.post(
        "/organizations",
        headers=authenticated_headers,
        json={"name": name},
    )

    assert response.status_code == 201
    response_body = response.json()

    with session_factory() as session:
        persisted_organization = (
            session.execute(
                text(
                    "SELECT id, name, created_at FROM organizations WHERE name = :name"
                ),
                {"name": name},
            )
            .mappings()
            .one()
        )

    assert str(persisted_organization["id"]) == response_body["id"]
    assert persisted_organization["name"] == name
    assert persisted_organization["created_at"].tzinfo is not None


def test_create_organization_creates_admin_membership(
    authenticated_user_id: UUID,
    authenticated_headers: dict[str, str],
) -> None:
    response = client.post(
        "/organizations",
        headers=authenticated_headers,
        json={
            "name": "organization_name",
        },
    )

    assert response.status_code == 201
    response_body = response.json()
    organization_id = response_body["id"]

    with session_factory() as session:
        persisted_membership = (
            session.execute(
                text(
                    "SELECT role, organization_id, user_id "
                    "FROM organization_memberships "
                    "WHERE organization_id = :id"
                ),
                {"id": organization_id},
            )
            .mappings()
            .one_or_none()
        )

    assert persisted_membership is not None
    assert persisted_membership["role"] == "admin"
    assert persisted_membership["organization_id"] == UUID(organization_id)
    assert persisted_membership["user_id"] == authenticated_user_id


def test_create_organization_rejects_request_without_access_token() -> None:
    response = client.post(
        "/organizations",
        json={
            "name": "organization_name",
        },
    )

    assert response.status_code == 401


def test_get_organization_returns_organization_for_admin(
    make_organization: Callable[[str], UUID],
    authenticated_user_id: UUID,
    authenticated_headers: dict[str, str],
) -> None:
    organization_name = "organization_name_value"
    organization_id = make_organization(organization_name)
    with session_factory() as session:
        membership = OrganizationMembership(
            organization_id=organization_id,
            user_id=authenticated_user_id,
            role="admin",
        )
        session.add(membership)
        session.commit()

    response = client.get(
        f"/organizations/{organization_id}",
        headers=authenticated_headers,
    )

    assert response.status_code == 200

    response_body = response.json()

    assert response_body["id"] == str(organization_id)
    assert response_body["name"] == organization_name

    created_at = response_body["created_at"]
    assert "T" in created_at
    assert datetime.fromisoformat(created_at).tzinfo is not None


def test_get_organization_returns_organization_for_operator(
    make_organization: Callable[[str], UUID],
    authenticated_user_id: UUID,
    authenticated_headers: dict[str, str],
) -> None:
    organization_name = "organization_name_value"
    organization_id = make_organization(organization_name)
    with session_factory() as session:
        membership = OrganizationMembership(
            organization_id=organization_id,
            user_id=authenticated_user_id,
            role="operator",
        )
        session.add(membership)
        session.commit()

    response = client.get(
        f"/organizations/{organization_id}",
        headers=authenticated_headers,
    )

    assert response.status_code == 200

    response_body = response.json()

    assert response_body["id"] == str(organization_id)
    assert response_body["name"] == organization_name

    created_at = response_body["created_at"]
    assert "T" in created_at
    assert datetime.fromisoformat(created_at).tzinfo is not None


def test_get_organization_rejects_no_access_token(
    organization_id: UUID,
) -> None:
    response = client.get(
        f"/organizations/{organization_id}",
    )

    assert response.status_code == 401


def test_get_organization_rejects_member_of_another_organization(
    make_organization: Callable[[str], UUID],
    admin_authenticated_headers: dict[str, str],
) -> None:
    organization_id = make_organization("new_organization_name_value")
    response = client.get(
        f"/organizations/{organization_id}",
        headers=admin_authenticated_headers,
    )

    assert response.status_code == 403
