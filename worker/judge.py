from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from sqlalchemy.orm import Session

from backend.app.artifact_service import (
    load_problem_testcases,
    load_sample_run_source,
    load_submission_source,
    store_sample_run_result,
    store_submission_result,
)
from backend.app.attempt_service import (
    enqueue_llm_report_or_mark_error,
    finalize_exam_attempt,
)
from backend.app.database import SessionLocal
from backend.app.models import SampleRun, Submission
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
        report = finalize_exam_attempt(db, submission.exam_attempt_id)
        db.commit()
        if report is not None:
            db.refresh(report)
            enqueue_llm_report_or_mark_error(db, report)
        return

    problem = submission.problem
    source_code = load_submission_source(submission)
    testcases = load_problem_testcases(problem)

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
    testcase_results: list[dict[str, object]] = []

    # 모든 테스트케이스를 병렬로 동시에 실행
    max_workers = min(len(testcases), 8)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(
                run_python_code,
                source_code,
                str(testcase["input"]),
                problem.time_limit_ms,
                problem.memory_limit_mb,
            )
            for testcase in testcases
        ]
        all_results = [f.result() for f in futures]

    for testcase, result in zip(testcases, all_results):
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
            testcase_results.append(
                _testcase_result(testcase, result, passed=False, message=error_message)
            )
            break

        user_output = normalize_output(str(result.get("stdout", "")))
        expected_output = normalize_output(str(testcase["expected_output"]))

        if user_output == expected_output:
            passed_count += 1
            testcase_results.append(_testcase_result(testcase, result, passed=True))
            continue

        final_status = "WRONG_ANSWER"
        error_message = "Wrong answer"
        testcase_results.append(
            _testcase_result(testcase, result, passed=False, message=error_message)
        )
        break

    score = int((passed_count / len(testcases)) * 100)
    store_submission_result(
        submission,
        {
            "submission_id": submission.id,
            "problem_id": submission.problem_id,
            "status": final_status,
            "score": score,
            "passed_count": passed_count,
            "total_count": len(testcases),
            "execution_time_ms": max_execution_time_ms,
            "error_message": error_message,
            "testcase_results": testcase_results,
        },
    )

    submission.status = final_status
    submission.score = score
    submission.passed_count = passed_count
    submission.total_count = len(testcases)
    submission.execution_time_ms = max_execution_time_ms
    submission.memory_mb = 0
    submission.error_message = error_message
    report = finalize_exam_attempt(db, submission.exam_attempt_id)
    db.commit()
    if report is not None:
        db.refresh(report)
        enqueue_llm_report_or_mark_error(db, report)


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
        source_code=load_sample_run_source(sample_run),
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
    store_sample_run_result(
        sample_run,
        {
            "sample_run_id": sample_run.id,
            "problem_id": sample_run.problem_id,
            "sample_index": sample_run.sample_index,
            "status": sample_run.status,
            "stdout": sample_run.stdout,
            "stderr": sample_run.stderr,
            "execution_time_ms": sample_run.execution_time_ms,
        },
    )
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
    report = finalize_exam_attempt(db, submission.exam_attempt_id)
    db.commit()
    if report is not None:
        db.refresh(report)
        enqueue_llm_report_or_mark_error(db, report)


def _testcase_result(
    testcase: dict[str, object],
    result: dict[str, object],
    passed: bool,
    message: str | None = None,
) -> dict[str, object]:
    return {
        "testcase_id": testcase.get("id"),
        "is_hidden": bool(testcase.get("is_hidden", True)),
        "passed": passed,
        "status": str(result["status"]),
        "execution_time_ms": int(result.get("execution_time_ms", 0)),
        "stdout": str(result.get("stdout", "")),
        "stderr": str(result.get("stderr", "")),
        "message": message,
    }
