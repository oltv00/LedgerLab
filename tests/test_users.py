from collections.abc import Generator
from datetime import datetime
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, text

from ledgerlab.database import session_factory
from ledgerlab.main import app
from ledgerlab.models import User

client = TestClient(app=app)


@pytest.fixture(autouse=True)
def clear_users() -> Generator[None]:
    with session_factory() as session:
        session.execute(delete(User))
        session.commit()

    yield

    with session_factory() as session:
        session.execute(delete(User))
        session.commit()


def test_create_user_returns_created_user() -> None:
    response = client.post(
        "/users",
        json={"name": "user_name_value", "email": "user_email@email.user"},
    )

    assert response.status_code == 201
    response_body = response.json()

    assert response_body["name"] == "user_name_value"
    assert UUID(response_body["id"])
    assert response_body["email"] == "user_email@email.user"

    created_at = response_body["created_at"]
    assert "T" in created_at
    assert datetime.fromisoformat(created_at).tzinfo is not None


def test_create_user_rejects_invalid_email() -> None:
    response = client.post(
        "/users",
        json={"name": "user_name_value", "email": "not-an-email"},
    )

    assert response.status_code == 422


def test_create_user_rejects_whitespace_only_name() -> None:
    response = client.post(
        "/users",
        json={"name": "     ", "email": "user_email@email.user"},
    )

    assert response.status_code == 422


def test_create_user_trims_surrounding_whitespace() -> None:
    response = client.post(
        "/users",
        json={"name": "   user_name_value   ", "email": "user_email@email.user"},
    )

    assert response.status_code == 201
    assert response.json()["name"] == "user_name_value"


def test_create_user_trims_surrounding_email_whitespace() -> None:
    response = client.post(
        "/users",
        json={"name": "user_name_value", "email": "   user_email@email.user   "},
    )

    assert response.status_code == 201
    assert response.json()["email"] == "user_email@email.user"


def test_create_user_persists_user() -> None:
    name = "user_name_value"
    email = "user_email_value@domain.com"

    response = client.post(
        "/users",
        json={"name": name, "email": email},
    )

    assert response.status_code == 201
    response_body = response.json()

    with session_factory() as session:
        persisted_user = (
            session.execute(
                text(
                    "SELECT id, name, email, created_at FROM users WHERE email = :email"
                ),
                {"email": email},
            )
            .mappings()
            .one()
        )

    assert str(persisted_user["id"]) == response_body["id"]
    assert persisted_user["name"] == name
    assert persisted_user["email"] == email
    assert persisted_user["created_at"].tzinfo is not None
