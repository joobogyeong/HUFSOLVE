from __future__ import annotations

from sqlalchemy.orm import Session

from .config import settings
from .models import ExamAttempt, LlmReport, Submission
from .queue.factory import get_queue_client


TERMINAL_SUBMISSION_STATUSES = {
    "ACCEPTED",
    "WRONG_ANSWER",
    "TIME_LIMIT_EXCEEDED",
    "MEMORY_LIMIT_EXCEEDED",
    "OUTPUT_LIMIT_EXCEEDED",
    "RUNTIME_ERROR",
    "SYSTEM_ERROR",
}


def finalize_exam_attempt(db: Session, attempt_id: int | None) -> LlmReport | None:
    if attempt_id is None:
        return None

    attempt = (
        db.query(ExamAttempt)
        .filter(ExamAttempt.id == attempt_id)
        .with_for_update()
        .one_or_none()
    )
    if attempt is None or attempt.status != "GRADING":
        return None

    submissions = (
        db.query(Submission)
        .filter(Submission.exam_attempt_id == attempt.id)
        .order_by(Submission.problem_id.asc())
        .all()
    )
    if not submissions or any(
        submission.status not in TERMINAL_SUBMISSION_STATUSES
        for submission in submissions
    ):
        return None

    passed_problems = sum(
        1 for submission in submissions if submission.status == "ACCEPTED"
    )
    attempt.passed_problems = passed_problems
    attempt.total_problems = len(submissions)
    attempt.score = round((passed_problems / len(submissions)) * 100)
    attempt.status = (
        "SYSTEM_ERROR"
        if any(submission.status == "SYSTEM_ERROR" for submission in submissions)
        else "COMPLETED"
    )

    if attempt.llm_report is not None:
        return None

    report = LlmReport(
        exam_attempt_id=attempt.id,
        student_id=attempt.student_id,
        status="PENDING",
        model_id=settings.bedrock_review_model_id,
    )
    db.add(report)
    return report


def enqueue_llm_report_or_mark_error(db: Session, report: LlmReport | None) -> None:
    if report is None:
        return

    try:
        get_queue_client().enqueue_llm_report(report.id)
    except Exception as exc:
        report.status = "SYSTEM_ERROR"
        report.error_message = f"Failed to enqueue LLM report: {exc}"[:2000]
        db.commit()
