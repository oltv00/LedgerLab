from collections.abc import Generator
from datetime import datetime
from uuid import UUID

import jwt
import pytest
from fastapi.testclient import TestClient
from pwdlib import PasswordHash
from sqlalchemy import text

from ledgerlab.database import session_factory
from ledgerlab.main import app
from ledgerlab.models import User

client = TestClient(app=app)
password_hashing = PasswordHash.recommended()


@pytest.fixture
def registered_user_id() -> Generator[UUID]:
    with session_factory() as session:
        password = "8c647eab31fe"
        user = User(name="user_name_value", email="email_value@domain.com")
        user.password_hash = password_hashing.hash(password)

        session.add(user)
        session.commit()
        session.refresh(user)

    yield user.id


@pytest.fixture
def jwt_secret(monkeypatch: pytest.MonkeyPatch) -> str:
    secret = "04a58a7a876cdbeeee87ceaa6c9608caf60ec6a52eea4a950da39d6c50910bf2"
    monkeypatch.setenv("JWT_SECRET", secret)
    return secret


@pytest.fixture
def user_without_password_hash_email() -> Generator[str]:
    with session_factory() as session:
        user = User(name="user_name_value", email="email_value@domain.com")
        session.add(user)
        session.commit()
        session.refresh(user)

    yield user.email


def test_login_returns_access_and_refresh_tokens(
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
    refresh_token = response.json()["refresh_token"]

    algorithms = ["HS256"]

    access_token_claims = jwt.decode(
        access_token,
        key=jwt_secret,
        algorithms=algorithms,
        options={"require": ["sub", "exp", "typ"]},
    )

    refresh_token_claims = jwt.decode(
        refresh_token,
        key=jwt_secret,
        algorithms=algorithms,
        options={"require": ["sub", "exp", "typ", "jti"]},
    )

    assert access_token_claims["sub"] == str(registered_user_id)
    assert refresh_token_claims["sub"] == str(registered_user_id)

    assert "exp" in access_token_claims
    assert "exp" in refresh_token_claims

    assert access_token_claims["typ"] == "access"
    assert refresh_token_claims["typ"] == "refresh"

    assert len(refresh_token_claims["jti"]) != 0

    jti = refresh_token_claims["jti"]

    with session_factory() as session:
        existed_refresh_token = (
            session.execute(
                text(
                    "SELECT user_id, jti, expires_at, revoked_at "
                    "FROM refresh-tokens "
                    "WHERE jti = :jti"
                ),
                {
                    "jti": jti,
                },
            )
            .mappings()
            .one()
        )

        assert existed_refresh_token["jti"] == jti
        assert existed_refresh_token["user_id"] == str(registered_user_id)

        expires_at = datetime.fromisoformat(refresh_token_claims["exp"])
        assert existed_refresh_token["expires_at"] == expires_at

        assert existed_refresh_token["revoked_at"] is None


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
