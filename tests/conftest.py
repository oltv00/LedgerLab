from collections.abc import Generator

import pytest
from sqlalchemy import delete

from ledgerlab.database import session_factory
from ledgerlab.models import Organization, OrganizationMembership, User


@pytest.fixture(autouse=True)
def reset_database() -> Generator[None]:
    with session_factory() as session:
        session.execute(delete(OrganizationMembership))
        session.execute(delete(User))
        session.execute(delete(Organization))
        session.commit()

    yield

    with session_factory() as session:
        session.execute(delete(OrganizationMembership))
        session.execute(delete(User))
        session.execute(delete(Organization))
        session.commit()
