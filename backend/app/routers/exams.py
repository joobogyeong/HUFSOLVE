from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..models import Exam, Problem
from ..schemas import ExamRead, ProblemRead

router = APIRouter(tags=["exams"])


@router.get("/exams", response_model=list[ExamRead])
def list_exams(db: Session = Depends(get_db)) -> list[ExamRead]:
    exams = (
        db.query(Exam)
        .options(selectinload(Exam.problems))
        .order_by(Exam.starts_at.asc(), Exam.id.asc())
        .all()
    )
    return [ExamRead.from_model(exam) for exam in exams]


@router.get("/exams/{room_code}", response_model=ExamRead)
def get_exam(room_code: str, db: Session = Depends(get_db)) -> ExamRead:
    exam = (
        db.query(Exam)
        .options(selectinload(Exam.problems))
        .filter(Exam.room_code == room_code.upper())
        .one_or_none()
    )

    if exam is None:
        raise HTTPException(status_code=404, detail="Exam not found")

    return ExamRead.from_model(exam)


@router.get("/problems/{problem_id}", response_model=ProblemRead)
def get_problem(problem_id: int, db: Session = Depends(get_db)) -> ProblemRead:
    problem = db.get(Problem, problem_id)

    if problem is None:
        raise HTTPException(status_code=404, detail="Problem not found")

    return ProblemRead.from_model(problem)
