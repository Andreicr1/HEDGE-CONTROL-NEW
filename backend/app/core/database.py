import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import Session, sessionmaker


def get_database_url() -> str:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is required")
    return database_url


database_url = get_database_url()
is_sqlite = database_url.startswith("sqlite")
connect_args = {"check_same_thread": False} if is_sqlite else {}
engine_kwargs = {"pool_pre_ping": True, "connect_args": connect_args}
if is_sqlite and ":memory:" in database_url:
    engine_kwargs["poolclass"] = StaticPool

engine = create_engine(database_url, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_session() -> Generator[Session, None, None]:
    session: Session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
