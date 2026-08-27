from collections.abc import Generator

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
# - whitespace validation;
# - database persistence across restarts;
# - duplicate organization behavior;
# - authentication.
def test_create_organization_returns_created_name() -> None:
    response = client.post(
        '/organizations',
        json={'name': 'Acme Operations'}
    )

    assert response.status_code == 201
    response_body = response.json()

    assert response_body['name'] == 'Acme Operations'
    assert 'id' in response_body
    assert 'created_at' in response_body
