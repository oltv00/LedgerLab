from datetime import UTC, datetime, timedelta

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
