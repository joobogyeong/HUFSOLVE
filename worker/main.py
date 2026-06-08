from __future__ import annotations

import argparse
import time

from backend.app.config import settings
from backend.app.database import SessionLocal, init_db
from backend.app.seed import seed_database
from worker.judge import judge_sample_run, judge_submission
from worker.queue import WorkerMessage, build_worker_queue
from worker.review import generate_llm_report


def process_message(message: WorkerMessage) -> None:
    if message.task_type == "llm_report":
        generate_llm_report(message.resource_id)
        return

    if message.task_type == "sample_run":
        judge_sample_run(message.resource_id)
        return

    judge_submission(message.resource_id)


def run_once() -> bool:
    queue = build_worker_queue()
    message = queue.receive()
    if message is None:
        return False

    try:
        process_message(message)
        queue.ack(message)
        return True
    except Exception as exc:
        queue.fail(message, exc)
        print(f"Failed to process {message.task_type}_id={message.resource_id}: {exc}")
        return False


def run_forever() -> None:
    queue = build_worker_queue()
    print(f"Worker started with queue_backend={settings.queue_backend}")

    while True:
        message = queue.receive()
        if message is None:
            if settings.queue_backend != "sqs":
                time.sleep(settings.worker_poll_wait_seconds)
            continue

        try:
            process_message(message)
            queue.ack(message)
            print(f"Finished {message.task_type}_id={message.resource_id}")
        except Exception as exc:
            queue.fail(message, exc)
            print(f"Failed to process {message.task_type}_id={message.resource_id}: {exc}")


def prepare_local_database() -> None:
    if settings.auto_create_tables:
        init_db()

    if settings.auto_seed:
        db = SessionLocal()
        try:
            seed_database(db)
        finally:
            db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="HUFSOLVE judge worker")
    parser.add_argument("--once", action="store_true", help="process at most one message")
    args = parser.parse_args()

    prepare_local_database()

    if args.once:
        processed = run_once()
        print("processed=1" if processed else "processed=0")
        return

    run_forever()


if __name__ == "__main__":
    main()
