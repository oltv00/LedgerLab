from fastapi.testclient import TestClient

from ledgerlab.main import app

client = TestClient(app)

# For this first red test, do not assert:
# - UUID format;
# - timestamp format;
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
    assert response.json()['name'] == 'Acme Operations'
