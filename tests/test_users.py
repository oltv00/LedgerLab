from datetime import datetime
from uuid import UUID

from fastapi.testclient import TestClient

from ledgerlab.main import app

client = TestClient(app=app)

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
    assert 'T' in created_at
    assert datetime.fromisoformat(created_at).tzinfo is not None

def test_create_user_rejects_invalid_email() -> None:
    response = client.post(
        "/users",
        json={
            "name": "user_name_value",
            "email": "not-an-email"
        },
    )

    assert response.status_code == 422
