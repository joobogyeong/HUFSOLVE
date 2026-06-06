from __future__ import annotations

import argparse

from .database import SessionLocal, init_db
from .seed import (
    seed_database,
    synchronize_execution_artifacts,
    synchronize_problem_artifacts,
    synchronize_reference_data,
)


def bootstrap_storage(seed_if_empty: bool = False) -> None:
    init_db()
    db = SessionLocal()
    try:
        if seed_if_empty:
            seed_database(db)
            return

        synchronize_reference_data(db)
        synchronize_problem_artifacts(db)
        synchronize_execution_artifacts(db)
        db.commit()
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create HUFSOLVE relational tables and synchronize artifact objects.",
    )
    parser.add_argument(
        "--seed-if-empty",
        action="store_true",
        help="Insert demo exams when the database has no exams before synchronizing storage.",
    )
    args = parser.parse_args()
    bootstrap_storage(seed_if_empty=args.seed_if_empty)


if __name__ == "__main__":
    main()
