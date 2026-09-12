from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from pwdlib import PasswordHash
from sqlalchemy import delete

from ledgerlab.database import session_factory
from ledgerlab.main import app
from ledgerlab.models import User

client = TestClient(app=app)
password_hashing = PasswordHash.recommended()


@pytest.fixture(autouse=True)
def clear_and_add_user_before_and_clear_after() -> Generator[None]:
    with session_factory() as session:
        session.execute(delete(User))

        password = "8c647eab31fe"
        user = User(name="user_name_value", email="email_value@domain.com")
        user.password_hash = password_hashing.hash(password)

        session.add(user)
        session.commit()

    yield

    with session_factory() as session:
        session.execute(delete(User))
        session.commit()


def test_login_returns_access_token() -> None:
    response = client.post(
        "/auth/login",
        json={
            "email": "email_value@domain.com",
            "password": "8c647eab31fe",
        },
    )

    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_rejects_wrong_password() -> None:
    response = client.post(
        "/auth/login",
        json={
            "email": "email_value@domain.com",
            "password": "8c647eab31fe_WRONG",
        },
    )

    assert response.status_code == 401


def test_login_rejects_unknown_email() -> None:
    response = client.post(
        "/auth/login",
        json={
            "email": "email_value_not_found@domain.com",
            "password": "8c647eab31fe",
        },
    )

    assert response.status_code == 401
