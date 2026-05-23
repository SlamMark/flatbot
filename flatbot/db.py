from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from flatbot.config import settings


def _make_engine(url: str):  # type: ignore[no-untyped-def]
    kw = {}
    if url.startswith("sqlite"):
        kw["connect_args"] = {"check_same_thread": False}
    return create_engine(url, echo=False, **kw)


engine = _make_engine(settings.database_url)


@event.listens_for(engine, "connect")
def _sqlite_pragmas(dbapi_conn, _record):  # type: ignore[no-untyped-def]
    if settings.database_url.startswith("sqlite"):
        dbapi_conn.execute("PRAGMA journal_mode=WAL")
        dbapi_conn.execute("PRAGMA busy_timeout=5000")
        dbapi_conn.execute("PRAGMA foreign_keys=ON")


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
