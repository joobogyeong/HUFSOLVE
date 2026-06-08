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
    _ensure_exam_attempt_columns()
    _ensure_submission_exam_attempt_column()


def _ensure_problem_reference_solution_column() -> None:
    inspector = inspect(engine)
    if "problems" not in inspector.get_table_names():
        return

    column_names = {column["name"] for column in inspector.get_columns("problems")}
    if "reference_solution" in column_names:
        return

    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE problems ADD COLUMN reference_solution TEXT"))


def _ensure_exam_attempt_columns() -> None:
    inspector = inspect(engine)
    if "exam_attempts" not in inspector.get_table_names():
        return

    column_names = {column["name"] for column in inspector.get_columns("exam_attempts")}
    with engine.begin() as connection:
        if "finalization_key" not in column_names:
            connection.execute(
                text("ALTER TABLE exam_attempts ADD COLUMN finalization_key VARCHAR(255)")
            )

    inspector = inspect(engine)
    finalization_indexes = [
        index
        for index in inspector.get_indexes("exam_attempts")
        if index.get("column_names") == ["finalization_key"]
    ]
    if not finalization_indexes:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "CREATE UNIQUE INDEX uq_exam_attempts_finalization_key "
                    "ON exam_attempts (finalization_key)"
                )
            )


def _ensure_submission_exam_attempt_column() -> None:
    inspector = inspect(engine)
    if "submissions" not in inspector.get_table_names():
        return

    column_names = {column["name"] for column in inspector.get_columns("submissions")}
    if "exam_attempt_id" not in column_names:
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE submissions ADD COLUMN exam_attempt_id INTEGER")
            )

    inspector = inspect(engine)
    exam_attempt_indexes = [
        index
        for index in inspector.get_indexes("submissions")
        if index.get("column_names") == ["exam_attempt_id"]
    ]
    if not exam_attempt_indexes:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "CREATE INDEX ix_submissions_exam_attempt_id "
                    "ON submissions (exam_attempt_id)"
                )
            )


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
