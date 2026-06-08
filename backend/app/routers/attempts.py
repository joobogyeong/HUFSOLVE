from __future__ import annotations

import hashlib

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from ..artifact_service import store_submission_source
from ..attempt_service import (
    enqueue_llm_report_or_mark_error,
    finalize_exam_attempt,
)
from ..database import get_db
from ..models import Exam, ExamAttempt, Submission
from ..queue.factory import get_queue_client
from ..schemas import ExamAttemptCreate, ExamAttemptRead
from ..seed import enroll_student_for_exam

router = APIRouter(tags=["exam-attempts"])


@router.post("/exam-attempts", response_model=ExamAttemptRead, status_code=202)
def create_exam_attempt(
    request: ExamAttemptCreate,
    db: Session = Depends(get_db),
) -> ExamAttemptRead:
    exam = (
        db.query(Exam)
        .options(joinedload(Exam.problems))
        .filter(Exam.room_code == request.room_code.upper())
        .one_or_none()
    )
    if exam is None:
        raise HTTPException(status_code=404, detail="Exam not found")

    finalization_key = _finalization_key(exam.id, request.student_id)
    existing = _get_existing_attempt(db, exam.id, request.student_id, finalization_key)
    if existing is not None:
        return ExamAttemptRead.from_model(existing)

    answers_by_problem = {answer.problem_id: answer for answer in request.answers}
    exam_problem_ids = {problem.id for problem in exam.problems}
    if len(answers_by_problem) != len(request.answers):
        raise HTTPException(status_code=400, detail="Duplicate problem answers")
    if set(answers_by_problem) != exam_problem_ids:
        raise HTTPException(
            status_code=400,
            detail="Answers must include every problem in the exam exactly once",
        )

    attempt = ExamAttempt(
        finalization_key=finalization_key,
        exam_id=exam.id,
        student_id=request.student_id,
        student_name=request.student_name,
        status="GRADING",
        score=0,
        passed_problems=0,
        total_problems=len(exam.problems),
    )
    db.add(attempt)
    enroll_student_for_exam(db, exam, request.student_id, request.student_name)
    db.flush()

    submissions: list[Submission] = []
    for problem in exam.problems:
        answer = answers_by_problem[problem.id]
        submission = Submission(
            exam_attempt_id=attempt.id,
            exam_id=exam.id,
            problem_id=problem.id,
            student_id=request.student_id,
            student_name=request.student_name,
            language=answer.language,
            source_code=answer.source_code,
            status="PENDING",
            total_count=len(problem.testcases),
        )
        db.add(submission)
        db.flush()
        store_submission_source(submission, answer.source_code)
        submissions.append(submission)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = _get_existing_attempt(db, exam.id, request.student_id, finalization_key)
        if existing is None:
            raise
        return ExamAttemptRead.from_model(existing)

    submission_ids = [submission.id for submission in submissions]
    try:
        failed_ids = get_queue_client().enqueue_submissions(submission_ids)
    except Exception:
        failed_ids = submission_ids
    report = None
    if failed_ids:
        db.query(Submission).filter(Submission.id.in_(failed_ids)).update(
            {
                "status": "SYSTEM_ERROR",
                "error_message": "Failed to enqueue submission",
            },
            synchronize_session=False,
        )
        report = finalize_exam_attempt(db, attempt.id)
        db.commit()
        if report is not None:
            db.refresh(report)
            enqueue_llm_report_or_mark_error(db, report)

    db.refresh(attempt)
    return ExamAttemptRead.from_model(attempt)


@router.get("/exam-attempts", response_model=list[ExamAttemptRead])
def list_exam_attempts(
    student_id: str = Query(alias="studentId", min_length=1),
    db: Session = Depends(get_db),
) -> list[ExamAttemptRead]:
    attempts = (
        db.query(ExamAttempt)
        .options(joinedload(ExamAttempt.exam), joinedload(ExamAttempt.llm_report))
        .filter(ExamAttempt.student_id == student_id)
        .order_by(ExamAttempt.submitted_at.desc(), ExamAttempt.id.desc())
        .all()
    )
    return [ExamAttemptRead.from_model(attempt) for attempt in attempts]


@router.get("/exam-attempts/{attempt_id}", response_model=ExamAttemptRead)
def get_exam_attempt(attempt_id: int, db: Session = Depends(get_db)) -> ExamAttemptRead:
    attempt = (
        db.query(ExamAttempt)
        .options(joinedload(ExamAttempt.exam), joinedload(ExamAttempt.llm_report))
        .filter(ExamAttempt.id == attempt_id)
        .one_or_none()
    )
    if attempt is None:
        raise HTTPException(status_code=404, detail="Exam attempt not found")
    return ExamAttemptRead.from_model(attempt)


def _finalization_key(exam_id: int, student_id: str) -> str:
    raw = f"{exam_id}:{student_id.strip()}".encode()
    return hashlib.sha256(raw).hexdigest()


def _get_attempt_by_key(db: Session, finalization_key: str) -> ExamAttempt | None:
    return (
        db.query(ExamAttempt)
        .options(joinedload(ExamAttempt.exam), joinedload(ExamAttempt.llm_report))
        .filter(ExamAttempt.finalization_key == finalization_key)
        .one_or_none()
    )


def _get_existing_attempt(
    db: Session,
    exam_id: int,
    student_id: str,
    finalization_key: str,
) -> ExamAttempt | None:
    attempt = _get_attempt_by_key(db, finalization_key)
    if attempt is not None:
        return attempt

    attempt = (
        db.query(ExamAttempt)
        .options(joinedload(ExamAttempt.exam), joinedload(ExamAttempt.llm_report))
        .filter(
            ExamAttempt.exam_id == exam_id,
            ExamAttempt.student_id == student_id,
        )
        .order_by(ExamAttempt.submitted_at.desc(), ExamAttempt.id.desc())
        .first()
    )
    if attempt is not None and not attempt.finalization_key:
        attempt.finalization_key = finalization_key
        db.commit()
        db.refresh(attempt)
    return attempt
