from __future__ import annotations

from sqlalchemy.orm import Session

from backend.app.database import SessionLocal
from backend.app.models import SampleRun, Submission, Testcase
from worker.docker_runner import run_python_code

TERMINAL_STATUSES = {
    "ACCEPTED",
    "WRONG_ANSWER",
    "TIME_LIMIT_EXCEEDED",
    "MEMORY_LIMIT_EXCEEDED",
    "OUTPUT_LIMIT_EXCEEDED",
    "RUNTIME_ERROR",
    "SYSTEM_ERROR",
}

TERMINAL_SAMPLE_RUN_STATUSES = {
    "COMPLETED",
    "TIME_LIMIT_EXCEEDED",
    "MEMORY_LIMIT_EXCEEDED",
    "OUTPUT_LIMIT_EXCEEDED",
    "RUNTIME_ERROR",
    "SYSTEM_ERROR",
}


def normalize_output(text: str) -> str:
    return "\n".join(line.rstrip() for line in text.strip().splitlines()).strip()


def judge_submission(submission_id: int) -> None:
    db = SessionLocal()
    try:
        _judge_submission(db, submission_id)
    finally:
        db.close()


def judge_sample_run(sample_run_id: int) -> None:
    db = SessionLocal()
    try:
        _judge_sample_run(db, sample_run_id)
    finally:
        db.close()


def _judge_submission(db: Session, submission_id: int) -> None:
    submission = db.get(Submission, submission_id)
    if submission is None:
        raise RuntimeError(f"Submission {submission_id} not found")

    if submission.status in TERMINAL_STATUSES:
        return

    problem = submission.problem
    testcases = (
        db.query(Testcase)
        .filter(Testcase.problem_id == submission.problem_id)
        .order_by(Testcase.id.asc())
        .all()
    )

    if not testcases:
        raise RuntimeError(f"Problem {submission.problem_id} has no testcases")

    submission.status = "RUNNING"
    submission.error_message = None
    submission.total_count = len(testcases)
    db.commit()

    passed_count = 0
    max_execution_time_ms = 0
    final_status = "ACCEPTED"
    error_message: str | None = None

    for testcase in testcases:
        result = run_python_code(
            source_code=submission.source_code,
            input_data=testcase.input_data,
            time_limit_ms=problem.time_limit_ms,
            memory_limit_mb=problem.memory_limit_mb,
        )
        execution_time_ms = int(result.get("execution_time_ms", 0))
        max_execution_time_ms = max(max_execution_time_ms, execution_time_ms)
        status = str(result["status"])

        if status in {
            "TIME_LIMIT_EXCEEDED",
            "MEMORY_LIMIT_EXCEEDED",
            "OUTPUT_LIMIT_EXCEEDED",
            "RUNTIME_ERROR",
        }:
            final_status = status
            error_message = str(result.get("stderr") or status)
            break

        user_output = normalize_output(str(result.get("stdout", "")))
        expected_output = normalize_output(testcase.expected_output)

        if user_output == expected_output:
            passed_count += 1
            continue

        final_status = "WRONG_ANSWER"
        error_message = "Wrong answer"
        break

    score = int((passed_count / len(testcases)) * 100)

    submission.status = final_status
    submission.score = score
    submission.passed_count = passed_count
    submission.total_count = len(testcases)
    submission.execution_time_ms = max_execution_time_ms
    submission.memory_mb = 0
    submission.error_message = error_message
    db.commit()


def _judge_sample_run(db: Session, sample_run_id: int) -> None:
    sample_run = db.get(SampleRun, sample_run_id)
    if sample_run is None:
        raise RuntimeError(f"Sample run {sample_run_id} not found")

    if sample_run.status in TERMINAL_SAMPLE_RUN_STATUSES:
        return

    sample_run.status = "RUNNING"
    sample_run.stderr = None
    db.commit()

    result = run_python_code(
        source_code=sample_run.source_code,
        input_data=sample_run.input_data,
        time_limit_ms=sample_run.problem.time_limit_ms,
        memory_limit_mb=sample_run.problem.memory_limit_mb,
    )
    status = str(result["status"])
    sample_run.stdout = str(result.get("stdout", ""))
    sample_run.stderr = str(result.get("stderr", "")) or None
    sample_run.execution_time_ms = int(result.get("execution_time_ms", 0))
    sample_run.memory_mb = 0
    sample_run.status = "COMPLETED" if status == "OK" else status
    db.commit()


def mark_submission_system_error(submission_id: int, message: str) -> None:
    db = SessionLocal()
    try:
        _mark_system_error(db, submission_id, message)
    finally:
        db.close()


def mark_sample_run_system_error(sample_run_id: int, message: str) -> None:
    db = SessionLocal()
    try:
        sample_run = db.get(SampleRun, sample_run_id)
        if sample_run is None:
            return

        sample_run.status = "SYSTEM_ERROR"
        sample_run.stderr = message[:2000]
        db.commit()
    finally:
        db.close()


def _mark_system_error(db: Session, submission_id: int, message: str) -> None:
    submission = db.get(Submission, submission_id)
    if submission is None:
        return

    submission.status = "SYSTEM_ERROR"
    submission.error_message = message[:2000]
    db.commit()
