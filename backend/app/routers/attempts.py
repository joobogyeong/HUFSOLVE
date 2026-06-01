from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..models import Exam, ExamAttempt, Submission
from ..schemas import ExamAttemptCreate, ExamAttemptRead

router = APIRouter(tags=["exam-attempts"])


@router.post("/exam-attempts", response_model=ExamAttemptRead, status_code=201)
def create_exam_attempt(
    request: ExamAttemptCreate,
    db: Session = Depends(get_db),
) -> ExamAttemptRead:
    exam = db.query(Exam).filter(Exam.room_code == request.room_code.upper()).one_or_none()
    if exam is None:
        raise HTTPException(status_code=404, detail="Exam not found")

    previous_attempt = (
        db.query(ExamAttempt)
        .filter(
            ExamAttempt.exam_id == exam.id,
            ExamAttempt.student_id == request.student_id,
        )
        .order_by(ExamAttempt.submitted_at.desc(), ExamAttempt.id.desc())
        .first()
    )

    total_problems = len(exam.problems)
    accepted_query = db.query(Submission.problem_id).filter(
        Submission.exam_id == exam.id,
        Submission.student_id == request.student_id,
        Submission.status == "ACCEPTED",
    )
    if previous_attempt is not None:
        accepted_query = accepted_query.filter(
            Submission.created_at > previous_attempt.submitted_at
        )

    passed_problems = accepted_query.distinct().count()
    score = round((passed_problems / total_problems) * 100) if total_problems else 0

    attempt = ExamAttempt(
        exam_id=exam.id,
        student_id=request.student_id,
        student_name=request.student_name,
        status=request.status,
        score=score,
        passed_problems=passed_problems,
        total_problems=total_problems,
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return ExamAttemptRead.from_model(attempt)


@router.get("/exam-attempts", response_model=list[ExamAttemptRead])
def list_exam_attempts(
    student_id: str = Query(alias="studentId", min_length=1),
    db: Session = Depends(get_db),
) -> list[ExamAttemptRead]:
    attempts = (
        db.query(ExamAttempt)
        .options(joinedload(ExamAttempt.exam))
        .filter(ExamAttempt.student_id == student_id)
        .order_by(ExamAttempt.submitted_at.desc(), ExamAttempt.id.desc())
        .all()
    )
    return [ExamAttemptRead.from_model(attempt) for attempt in attempts]
