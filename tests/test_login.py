from collections.abc import Generator
from uuid import UUID

import jwt
import pytest
from fastapi.testclient import TestClient
from pwdlib import PasswordHash
from sqlalchemy import delete

from ledgerlab.database import session_factory
from ledgerlab.main import app
from ledgerlab.models import User

client = TestClient(app=app)
password_hashing = PasswordHash.recommended()


@pytest.fixture
def registered_user_id() -> Generator[UUID]:
    with session_factory() as session:
        session.execute(delete(User))

        password = "8c647eab31fe"
        user = User(name="user_name_value", email="email_value@domain.com")
        user.password_hash = password_hashing.hash(password)

        session.add(user)
        session.commit()
        session.refresh(user)

    yield user.id

    with session_factory() as session:
        session.execute(delete(User))
        session.commit()


@pytest.fixture
def jwt_secret(monkeypatch: pytest.MonkeyPatch) -> str:
    secret = "04a58a7a876cdbeeee87ceaa6c9608caf60ec6a52eea4a950da39d6c50910bf2"
    monkeypatch.setenv("JWT_SECRET", secret)
    return secret


@pytest.fixture
def user_without_password_hash_email() -> Generator[str]:
    with session_factory() as session:
        session.execute(delete(User))

        user = User(name="user_name_value", email="email_value@domain.com")
        session.add(user)
        session.commit()
        session.refresh(user)

    yield user.email

    with session_factory() as session:
        session.execute(delete(User))
        session.commit()


def test_login_returns_access_token(
    registered_user_id: UUID,
    jwt_secret: str,
) -> None:
    response = client.post(
        "/auth/login",
        json={
            "email": "email_value@domain.com",
            "password": "8c647eab31fe",
        },
    )

    assert response.status_code == 200
    access_token = response.json()["access_token"]
    claims = jwt.decode(
        access_token,
        key=jwt_secret,
        algorithms=["HS256"],
        options={"require": ["sub", "exp"]},
    )
    assert claims["sub"] == str(registered_user_id)
    assert "exp" in claims


@pytest.mark.usefixtures("registered_user_id")
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


def test_login_without_password_hash(
    user_without_password_hash_email: str,
) -> None:
    response = client.post(
        "/auth/login",
        json={
            "email": user_without_password_hash_email,
            "password": "8c647eab31fe",
        },
    )

    assert response.status_code == 401
