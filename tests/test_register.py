from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, text

from ledgerlab.database import session_factory
from ledgerlab.main import app
from ledgerlab.models import User

client = TestClient(app=app)


@pytest.fixture(autouse=True)
def clear_register_users() -> Generator[None]:
    with session_factory() as session:
        session.execute(delete(User))
        session.commit()

    yield

    with session_factory() as session:
        session.execute(delete(User))
        session.commit()


def test_register_creates_user_with_hashed_password() -> None:
    password = "8c647eab31fe"
    response = client.post(
        "/auth/register",
        json={
            "name": "name_value",
            "email": "email_value@domain.com",
            "password": password,
        },
    )

    # valid registration → 201
    assert response.status_code == 201
    response_body = response.json()
    user_id = response_body["id"]

    # response does not expose password/password_hash
    assert "password" not in response_body
    assert "password_hash" not in response_body

    # database has a password hash
    with session_factory() as session:
        password_hash = (
            session.execute(
                text(
                    "SELECT password_hash FROM users where id = :user_id",
                ),
                {
                    "user_id": user_id,
                },
            )
        ).scalar_one()
        assert password_hash is not None
        assert password_hash != password
        assert password_hashing.verify(password, password_hash)


def test_register_rejects_less_than_min_password_length() -> None:
    response = client.post(
        "/auth/register",
        json={
            "name": "name_value",
            "email": "email_value@domain.com",
            "password": "8c647eab31f",
        },
    )
    assert response.status_code == 422


def test_register_rejects_more_than_max_password_length() -> None:
    response = client.post(
        "/auth/register",
        json={
            "name": "name_value",
            "email": "email_value@domain.com",
            "password": "01c5698fbda6642ead3e0c8967de1b01eba238f059b3596040012c70c00bdebac728132873959d7b8392c27ae45d89b780b3bb41a344f2f2956fc74830c1e9cce3",
        },
    )
    assert response.status_code == 422


def test_register_accepts_min_password_length() -> None:
    response = client.post(
        "/auth/register",
        json={
            "name": "name_value",
            "email": "email_value@domain.com",
            "password": "8c647eab31fe",
        },
    )
    assert response.status_code == 201


def test_register_accepts_max_password_length() -> None:
    response = client.post(
        "/auth/register",
        json={
            "name": "name_value",
            "email": "email_value@domain.com",
            "password": "01c5698fbda6642ead3e0c8967de1b01eba238f059b3596040012c70c00bdebac728132873959d7b8392c27ae45d89b780b3bb41a344f2f2956fc74830c1e9cc",
        },
    )
    assert response.status_code == 201
