from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..artifact_service import store_submission_source
from ..database import get_db
from ..models import Problem, Submission
from ..queue.factory import get_queue_client
from ..schemas import SubmissionCreate, SubmissionCreated, SubmissionRead
from ..seed import enroll_student_for_exam

router = APIRouter(tags=["submissions"])


@router.post("/submissions", response_model=SubmissionCreated, status_code=202)
def create_submission(
    request: SubmissionCreate,
    db: Session = Depends(get_db),
) -> SubmissionCreated:
    problem = db.get(Problem, request.problem_id)
    if problem is None:
        raise HTTPException(status_code=404, detail="Problem not found")

    total_count = len(problem.testcases)
    submission = Submission(
        exam_id=problem.exam_id,
        problem_id=problem.id,
        student_id=request.student_id,
        student_name=request.student_name,
        language=request.language,
        source_code=request.source_code,
        status="PENDING",
        total_count=total_count,
    )
    db.add(submission)
    db.flush()
    store_submission_source(submission, request.source_code)
    if request.student_id:
        enroll_student_for_exam(
            db,
            problem.exam,
            request.student_id,
            request.student_name or request.student_id,
        )
    db.commit()
    db.refresh(submission)

    try:
        get_queue_client().enqueue_submission(submission.id)
    except Exception as exc:
        submission.status = "SYSTEM_ERROR"
        submission.error_message = f"Failed to enqueue submission: {exc}"
        db.commit()
        raise HTTPException(status_code=502, detail="Failed to enqueue submission") from exc

    return SubmissionCreated(submission_id=submission.id, status=submission.status)


@router.get("/submissions/{submission_id}", response_model=SubmissionRead)
def get_submission(submission_id: int, db: Session = Depends(get_db)) -> SubmissionRead:
    submission = db.get(Submission, submission_id)

    if submission is None:
        raise HTTPException(status_code=404, detail="Submission not found")

    return SubmissionRead.from_model(submission)
