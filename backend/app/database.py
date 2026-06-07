from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings


class Base(DeclarativeBase):
    pass


connect_args = (
    {"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {}
)

engine = create_engine(settings.database_url, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    from . import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_problem_reference_solution_column()


def _ensure_problem_reference_solution_column() -> None:
    inspector = inspect(engine)
    if "problems" not in inspector.get_table_names():
        return

    column_names = {column["name"] for column in inspector.get_columns("problems")}
    if "reference_solution" in column_names:
        return

    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE problems ADD COLUMN reference_solution TEXT"))


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
