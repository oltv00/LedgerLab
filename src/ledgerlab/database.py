import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

database_url = os.environ["DATABASE_URL"]

engine = create_engine(database_url)
session_factory = sessionmaker(bind=engine)


def get_session() -> Generator[Session]:
    with session_factory() as session:
        yield session
