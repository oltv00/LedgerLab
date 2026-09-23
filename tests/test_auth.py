from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import jwt
import pytest
from fastapi.testclient import TestClient

from ledgerlab.database import session_factory
from ledgerlab.main import app
from ledgerlab.models import RefreshToken, User

client = TestClient(app=app)


@pytest.fixture
def jwt_secret(monkeypatch: pytest.MonkeyPatch) -> str:
    secret = "04a58a7a876cdbeeee87ceaa6c9608caf60ec6a52eea4a950da39d6c50910bf2"
    monkeypatch.setenv("JWT_SECRET", secret)
    return secret


@pytest.fixture
def user() -> User:
    with session_factory() as session:
        user = User(
            name="user_name_value",
            email="email_value@domain.com",
        )
        session.add(user)
        session.commit()
        session.refresh(user)
    return user


@pytest.fixture
def refresh_token(
    jwt_secret: str,
    user: User,
) -> str:
    exp = datetime.now(UTC) + timedelta(days=7)
    jti = uuid4()
    payload = {
        "sub": str(user.id),
        "exp": exp,
        "typ": "refresh",
        "jti": str(jti),
    }
    refresh_token = jwt.encode(
        payload=payload,
        key=jwt_secret,
        algorithm="HS256",
    )

    with session_factory() as session:
        db_refresh_token = RefreshToken(
            jti=jti,
            user_id=user.id,
            expires_at=exp,
            revoked_at=None,
        )
        session.add(db_refresh_token)
        session.commit()

    return refresh_token


@pytest.fixture
def refresh_token_payload(
    jwt_secret: str,
    refresh_token: str,
) -> dict[str, Any]:
    payload = jwt.decode(
        jwt=refresh_token,
        algorithms=["HS256"],
        key=jwt_secret,
        options={"require": ["sub", "exp", "jti", "typ"]},
    )
    return payload


@pytest.fixture
def access_token(
    jwt_secret: str,
    user: User,
) -> str:
    exp = datetime.now(UTC) + timedelta(minutes=15)
    payload = {
        "sub": str(user.id),
        "exp": exp,
        "typ": "access",
    }
    access_token = jwt.encode(
        payload=payload,
        key=jwt_secret,
        algorithm="HS256",
    )
    return access_token


def test_auth_refresh_revokes_presented_token(
    refresh_token: str,
    refresh_token_payload: dict[str, Any],
) -> None:
    with session_factory() as session:
        db_refresh_token = session.get(
            RefreshToken,
            refresh_token_payload["jti"],
        )

    assert db_refresh_token is not None
    assert db_refresh_token.revoked_at is None

    response = client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    assert response.status_code == 200

    with session_factory() as session:
        db_refresh_token = session.get(
            RefreshToken,
            refresh_token_payload["jti"],
        )

    assert db_refresh_token is not None
    assert db_refresh_token.revoked_at is not None


def test_auth_refresh_returns_a_replacement_refresh_token(
    jwt_secret: str,
    refresh_token: str,
    refresh_token_payload: dict[str, Any],
) -> None:
    response = client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert response.status_code == 200

    response_body = response.json()
    assert "access_token" in response_body
    assert "refresh_token" in response_body

    access_token = response_body["access_token"]
    access_token_payload = jwt.decode(
        jwt=access_token,
        algorithms=["HS256"],
        key=jwt_secret,
        options={"require": ["sub", "exp", "typ"]},
    )
    assert access_token_payload["typ"] == "access"
    assert access_token_payload["sub"] == refresh_token_payload["sub"]

    new_refresh_token = response_body["refresh_token"]
    new_refresh_token_payload = jwt.decode(
        jwt=new_refresh_token,
        algorithms=["HS256"],
        key=jwt_secret,
        options={"require": ["sub", "exp", "jti", "typ"]},
    )
    assert new_refresh_token_payload["typ"] == "refresh"
    assert new_refresh_token_payload["sub"] == refresh_token_payload["sub"]
    assert new_refresh_token_payload["jti"] != refresh_token_payload["jti"]
    assert "exp" in new_refresh_token_payload

    with session_factory() as session:
        db_refresh_token = session.get(RefreshToken, new_refresh_token_payload["jti"])
        old_db_refresh_token = session.get(RefreshToken, refresh_token_payload["jti"])

    assert db_refresh_token is not None
    assert db_refresh_token.user_id == UUID(new_refresh_token_payload["sub"])
    assert db_refresh_token.revoked_at is None

    assert old_db_refresh_token is not None
    assert old_db_refresh_token.revoked_at is not None

    assert db_refresh_token.user_id == old_db_refresh_token.user_id

    expires_at = datetime.fromtimestamp(
        new_refresh_token_payload["exp"],
        UTC,
    )
    assert db_refresh_token.expires_at == expires_at


def test_auth_refresh_rejects_replayed_refresh_token(
    refresh_token: str,
) -> None:
    response = client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert response.status_code == 200

    response = client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert response.status_code == 401


def test_auth_logout_revokes_submitted_refresh_token(
    refresh_token: str,
    refresh_token_payload: dict[str, Any],
) -> None:
    response = client.post(
        "/auth/logout",
        json={"refresh_token": refresh_token},
    )
    assert response.status_code == 204

    with session_factory() as session:
        db_refresh_token = session.get(
            RefreshToken,
            refresh_token_payload["jti"],
        )

    assert db_refresh_token is not None
    assert db_refresh_token.revoked_at is not None


def test_auth_logout_rejects_access_token(
    access_token: str,
) -> None:
    response = client.post(
        "/auth/logout",
        json={"refresh_token": access_token},
    )
    assert response.status_code == 401


def test_auth_refresh_rejects_access_token(
    access_token: str,
) -> None:
    response = client.post(
        "/auth/refresh",
        json={"refresh_token": access_token},
    )
    assert response.status_code == 401
