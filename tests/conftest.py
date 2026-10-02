from collections.abc import Callable, Generator
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
import pytest
from sqlalchemy import text

from ledgerlab.database import session_factory
from ledgerlab.models import (
    Organization,
    OrganizationMembership,
    User,
)


@pytest.fixture(autouse=True)
def reset_database() -> Generator[None]:
    with session_factory() as session:
        session.execute(
            text(
                "TRUNCATE TABLE "
                "ledger_entries, transfers, accounts, refresh_tokens, "
                "organization_memberships, users, organizations"
            )
        )
        session.commit()

    yield

    with session_factory() as session:
        session.execute(
            text(
                "TRUNCATE TABLE "
                "ledger_entries, transfers, accounts, refresh_tokens, "
                "organization_memberships, users, organizations"
            )
        )
        session.commit()


@pytest.fixture
def jwt_secret(monkeypatch: pytest.MonkeyPatch) -> str:
    secret = "15070f2063b42247ed95726766fdadc2058e3b3235b9ca752277e733d27f270e"
    monkeypatch.setenv("JWT_SECRET", secret)
    return secret


### Organization ###


@pytest.fixture
def create_organization_id() -> Callable[[str], UUID]:
    def create(name: str) -> UUID:
        with session_factory() as session:
            organization = Organization(name=name)
            session.add(organization)
            session.commit()
            session.refresh(organization)
        return organization.id

    return create


@pytest.fixture
def organization_id(create_organization_id) -> UUID:
    return create_organization_id("organization_name_value")


### Operator ###


@pytest.fixture
def operator_user_id() -> UUID:
    with session_factory() as session:
        user = User(
            name="operator_user_name_value",
            email="operator_email_value@domain.com",
        )
        session.add(user)
        session.commit()
        session.refresh(user)
    return user.id


@pytest.fixture
def operator_access_token_headers(
    jwt_secret: str,
    operator_user_id: UUID,
    organization_id: UUID,
) -> dict[str, str]:
    with session_factory() as session:
        organization_membership = OrganizationMembership(
            organization_id=organization_id,
            user_id=operator_user_id,
            role="operator",
        )
        session.add(organization_membership)
        session.commit()

    exp = datetime.now(UTC) + timedelta(minutes=1)
    payload = {
        "sub": str(operator_user_id),
        "exp": exp,
        "typ": "access",
    }
    access_token = jwt.encode(
        payload=payload,
        key=jwt_secret,
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def operator_access_token_headers_with_custom_organization_id(
    jwt_secret: str,
    operator_user_id: UUID,
) -> Callable[[UUID], dict[str, str]]:
    def make_headers(organization_id: UUID) -> dict[str, str]:
        with session_factory() as session:
            organization_membership = OrganizationMembership(
                organization_id=organization_id,
                user_id=operator_user_id,
                role="operator",
            )
            session.add(organization_membership)
            session.commit()

        exp = datetime.now(UTC) + timedelta(minutes=1)
        payload = {
            "sub": str(operator_user_id),
            "exp": exp,
            "typ": "access",
        }
        access_token = jwt.encode(
            payload=payload,
            key=jwt_secret,
            algorithm="HS256",
        )
        return {"Authorization": f"Bearer {access_token}"}

    return make_headers


### Admin ###


@pytest.fixture
def admin_user_id() -> UUID:
    with session_factory() as session:
        user = User(
            name="admin_user_name_value",
            email="admin_email_value@domain.com",
        )
        session.add(user)
        session.commit()
        session.refresh(user)
    return user.id


@pytest.fixture
def admin_access_token_headers(
    jwt_secret: str,
    admin_user_id: UUID,
    organization_id: UUID,
) -> dict[str, str]:
    with session_factory() as session:
        organization_membership = OrganizationMembership(
            organization_id=organization_id,
            user_id=admin_user_id,
            role="admin",
        )
        session.add(organization_membership)
        session.commit()

    exp = datetime.now(UTC) + timedelta(minutes=1)
    payload = {
        "sub": str(admin_user_id),
        "exp": exp,
        "typ": "access",
    }
    access_token = jwt.encode(
        payload=payload,
        key=jwt_secret,
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {access_token}"}
