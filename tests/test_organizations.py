from collections.abc import Generator
from datetime import datetime
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from ledgerlab.database import session_factory
from ledgerlab.main import app
from ledgerlab.models import Organization

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_organizations() -> Generator[None]:
    with session_factory() as session:
        session.execute(delete(Organization))
        session.commit()

    yield

    with session_factory() as session:
        session.execute(delete(Organization))
        session.commit()


# For this first red test, do not assert:
# - database persistence across restarts;
# - duplicate organization behavior;
# - authentication.
def test_create_organization_returns_created_organization() -> None:
    response = client.post("/organizations", json={"name": "Acme Operations"})

    assert response.status_code == 201
    response_body = response.json()

    assert response_body["name"] == "Acme Operations"
    assert UUID(response_body["id"])

    created_at = response_body["created_at"]
    assert "T" in created_at
    assert datetime.fromisoformat(created_at).tzinfo is not None


def test_create_organization_rejects_whitespace_only_name() -> None:
    response = client.post(
        "/organizations",
        json={"name": "    "},
    )

    assert response.status_code == 422


def test_create_organization_trims_surrounding_whitespace() -> None:
    response = client.post(
        "/organizations",
        json={"name": "   Acme Operations   "},
    )

    assert response.status_code == 201
    assert response.json()["name"] == "Acme Operations"
