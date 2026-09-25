from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Event
from typing import Any
from uuid import UUID, uuid4

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from ledgerlab.auth.auth_refresh import AuthRefreshRequest, get_refresh_token
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
    exp = (datetime.now(UTC) + timedelta(days=7)).replace(microsecond=0)
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


def test_auth_refresh_rejects_access_token(
    access_token: str,
) -> None:
    response = client.post(
        "/auth/refresh",
        json={"refresh_token": access_token},
    )
    assert response.status_code == 401


def test_auth_refresh_rejects_expired_refresh_token(
    jwt_secret: str,
    refresh_token_payload: dict[str, Any],
) -> None:
    refresh_token_payload["exp"] = datetime.now(UTC) - timedelta(minutes=15)
    refresh_token = jwt.encode(
        payload=refresh_token_payload,
        key=jwt_secret,
        algorithm="HS256",
    )

    response = client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    assert response.status_code == 401


def test_auth_refresh_rejects_invalid_signature_refresh_token(
    refresh_token_payload: dict[str, Any],
) -> None:
    refresh_token = jwt.encode(
        payload=refresh_token_payload,
        key="4747d7ef066d3a8c83fec3d9e4a75bfba1a7713b6aa6d7097f199de38e625a0a",
        algorithm="HS256",
    )

    response = client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    assert response.status_code == 401


@pytest.mark.usefixtures("jwt_secret")
def test_auth_refresh_rejects_empty_refresh_token() -> None:
    response = client.post(
        "/auth/refresh",
        json={"refresh_token": ""},
    )

    assert response.status_code == 401


@pytest.mark.usefixtures("jwt_secret")
def test_auth_refresh_rejects_null_refresh_token() -> None:
    response = client.post(
        "/auth/refresh",
        json={"refresh_token": None},
    )

    assert response.status_code == 401


@pytest.mark.usefixtures("jwt_secret")
def test_auth_refresh_rejects_missing_refresh_token() -> None:
    response = client.post(
        "/auth/refresh",
        json={},
    )

    assert response.status_code == 401


@pytest.mark.usefixtures("jwt_secret")
def test_auth_refresh_rejects_malformed_refresh_token() -> None:
    response = client.post(
        "/auth/refresh",
        json={"refresh_token": "not-a-jwt"},
    )

    assert response.status_code == 401


def test_auth_refresh_rejects_unknown_refresh_token(
    jwt_secret: str,
    refresh_token_payload: dict[str, Any],
) -> None:
    refresh_token_payload["jti"] = str(uuid4())
    refresh_token = jwt.encode(
        payload=refresh_token_payload,
        key=jwt_secret,
        algorithm="HS256",
    )

    response = client.post(
        "/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    assert response.status_code == 401


def test_auth_refresh_token_lock_prevents_concurrent_validation(
    refresh_token: str,
) -> None:
    first_lock_acquired = Event()
    release_first_lock = Event()

    def hold_first_lock() -> None:
        with session_factory() as session:
            get_refresh_token(
                request=AuthRefreshRequest(refresh_token=refresh_token),
                database_session=session,
            )
            first_lock_acquired.set()
            release_first_lock.wait()
            session.rollback()

    def try_to_acquire_second_lock() -> RefreshToken:
        with session_factory() as session:
            session.execute(
                text("SET LOCAL lock_timeout = '100ms'"),
            )
            return get_refresh_token(
                request=AuthRefreshRequest(refresh_token=refresh_token),
                database_session=session,
            )

    with ThreadPoolExecutor(max_workers=2) as executor:
        first_future = executor.submit(hold_first_lock)

        try:
            assert first_lock_acquired.wait(timeout=1)

            second_future = executor.submit(try_to_acquire_second_lock)

            with pytest.raises(OperationalError):
                second_future.result(timeout=1)

        finally:
            release_first_lock.set()

        first_future.result(timeout=1)


# --- Logout --- #


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


def test_auth_logout_rejects_replayed_refresh_token(
    refresh_token: str,
) -> None:
    response = client.post(
        "/auth/logout",
        json={"refresh_token": refresh_token},
    )
    assert response.status_code == 204

    response = client.post(
        "/auth/logout",
        json={"refresh_token": refresh_token},
    )
    assert response.status_code == 401


def test_auth_logout_rejects_expired_refresh_token(
    jwt_secret: str,
    refresh_token_payload: dict[str, Any],
) -> None:
    refresh_token_payload["exp"] = datetime.now(UTC) - timedelta(minutes=15)
    refresh_token = jwt.encode(
        payload=refresh_token_payload,
        key=jwt_secret,
        algorithm="HS256",
    )

    response = client.post(
        "/auth/logout",
        json={"refresh_token": refresh_token},
    )

    assert response.status_code == 401


def test_auth_logout_rejects_invalid_signature_refresh_token(
    refresh_token_payload: dict[str, Any],
) -> None:
    refresh_token = jwt.encode(
        payload=refresh_token_payload,
        key="4747d7ef066d3a8c83fec3d9e4a75bfba1a7713b6aa6d7097f199de38e625a0a",
        algorithm="HS256",
    )

    response = client.post(
        "/auth/logout",
        json={"refresh_token": refresh_token},
    )

    assert response.status_code == 401


@pytest.mark.usefixtures("jwt_secret")
def test_auth_logout_rejects_empty_refresh_token() -> None:
    response = client.post(
        "/auth/logout",
        json={"refresh_token": ""},
    )

    assert response.status_code == 401


@pytest.mark.usefixtures("jwt_secret")
def test_auth_logout_rejects_null_refresh_token() -> None:
    response = client.post(
        "/auth/logout",
        json={"refresh_token": None},
    )

    assert response.status_code == 401


@pytest.mark.usefixtures("jwt_secret")
def test_auth_logout_rejects_missing_refresh_token() -> None:
    response = client.post(
        "/auth/logout",
        json={},
    )

    assert response.status_code == 401


@pytest.mark.usefixtures("jwt_secret")
def test_auth_logout_rejects_malformed_refresh_token() -> None:
    response = client.post(
        "/auth/logout",
        json={"refresh_token": "not-a-jwt"},
    )

    assert response.status_code == 401


def test_auth_logout_rejects_unknown_refresh_token(
    jwt_secret: str,
    refresh_token_payload: dict[str, Any],
) -> None:
    refresh_token_payload["jti"] = str(uuid4())
    refresh_token = jwt.encode(
        payload=refresh_token_payload,
        key=jwt_secret,
        algorithm="HS256",
    )

    response = client.post(
        "/auth/logout",
        json={"refresh_token": refresh_token},
    )

    assert response.status_code == 401
