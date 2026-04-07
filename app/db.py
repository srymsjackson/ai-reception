"""Database engine and session utilities."""

from sqlmodel import SQLModel, Session, create_engine
from app.config import settings

connect_args = {}
if settings.database_url.startswith("sqlite"):
    # SQLite needs this flag because requests may run on different threads.
    connect_args = {"check_same_thread": False}

engine = create_engine(settings.database_url, echo=False, connect_args=connect_args)


def create_db_and_tables() -> None:
    """Create SQLModel tables from model metadata."""
    SQLModel.metadata.create_all(engine)


def get_session():
    """FastAPI dependency that yields a DB session per request."""
    with Session(engine) as session:
        yield session