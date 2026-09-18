from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest
from fastapi.testclient import TestClient

from ledgerlab.database import session_factory
from ledgerlab.main import app
from ledgerlab.models import User

client = TestClient(app=app)


@pytest.fixture
def jwt_secret(monkeypatch: pytest.MonkeyPatch) -> str:
    secret = "04a58a7a876cdbeeee87ceaa6c9608caf60ec6a52eea4a950da39d6c50910bf2"
    monkeypatch.setenv("JWT_SECRET", secret)
    return secret


def test_current_user(
    jwt_secret: str,
) -> None:
    with session_factory() as session:
        user = User(
            name="user_name_value",
            email="email_value@domain.com",
        )
        session.add(user)
        session.commit()
        session.refresh(user)

    exp = datetime.now(UTC) + timedelta(minutes=1)
    payload = {
        "sub": str(user.id),
        "exp": exp,
    }
    access_token = jwt.encode(
        payload=payload,
        key=jwt_secret,
        algorithm="HS256",
    )

    response = client.get(
        "/auth/me",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
    )

    assert response.status_code == 200

    expected_response = {
        "id": str(user.id),
        "name": "user_name_value",
        "email": "email_value@domain.com",
    }

    assert response.json() == expected_response


def test_current_user_rejects_token_with_non_uuid_subject(
    jwt_secret: str,
) -> None:
    exp = datetime.now(UTC) + timedelta(minutes=1)
    payload = {
        "sub": "not_an_uuid",
        "exp": exp,
    }
    access_token = jwt.encode(
        payload=payload,
        key=jwt_secret,
        algorithm="HS256",
    )

    response = client.get(
        "/auth/me",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
    )

    assert response.status_code == 401


def test_current_user_rejects_request_without_header() -> None:
    response = client.get(
        "/auth/me",
    )

    assert response.status_code == 401


def test_current_user_rejects_unknown_user(
    jwt_secret: str,
) -> None:
    exp = datetime.now(UTC) + timedelta(minutes=1)
    payload = {
        "sub": str(uuid4()),
        "exp": exp,
    }
    access_token = jwt.encode(
        payload=payload,
        key=jwt_secret,
        algorithm="HS256",
    )

    response = client.get(
        "/auth/me",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
    )

    assert response.status_code == 401


def test_current_user_rejects_expired_token(
    jwt_secret: str,
) -> None:
    with session_factory() as session:
        user = User(
            name="user_name_value",
            email="email_value@domain.com",
        )
        session.add(user)
        session.commit()
        session.refresh(user)

    exp = datetime.now(UTC) - timedelta(minutes=1)
    payload = {
        "sub": str(user.id),
        "exp": exp,
    }
    access_token = jwt.encode(
        payload=payload,
        key=jwt_secret,
        algorithm="HS256",
    )

    response = client.get(
        "/auth/me",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
    )

    assert response.status_code == 401


@pytest.mark.usefixtures("jwt_secret")
def test_current_user_rejects_not_a_jwt_in_header() -> None:
    response = client.get(
        "/auth/me",
        headers={
            "Authorization": "Bearer not-a-jwt",
        },
    )

    assert response.status_code == 401


@pytest.mark.usefixtures("jwt_secret")
def test_current_user_rejects_token_with_invalid_signature() -> None:
    with session_factory() as session:
        user = User(
            name="user_name_value",
            email="email_value@domain.com",
        )
        session.add(user)
        session.commit()
        session.refresh(user)

    exp = datetime.now(UTC) + timedelta(minutes=1)
    payload = {
        "sub": str(user.id),
        "exp": exp,
    }
    access_token = jwt.encode(
        payload=payload,
        key="e7af3fdd45645ad8bba468495db511e2ef38ade9de6b8383095d2cd14760a0fe",
        algorithm="HS256",
    )

    response = client.get(
        "/auth/me",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
    )

    assert response.status_code == 401
