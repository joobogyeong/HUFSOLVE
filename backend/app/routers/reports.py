from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import ExamAttempt, LlmReport
from ..schemas import LlmReportRead

router = APIRouter(tags=["reports"])


@router.get("/reports/{report_id}", response_model=LlmReportRead)
def get_report(report_id: int, db: Session = Depends(get_db)) -> LlmReportRead:
    report = db.get(LlmReport, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")

    return LlmReportRead.from_model(report)


@router.get("/exam-attempts/{attempt_id}/report", response_model=LlmReportRead)
def get_attempt_report(
    attempt_id: int,
    db: Session = Depends(get_db),
) -> LlmReportRead:
    attempt = db.get(ExamAttempt, attempt_id)
    if attempt is None:
        raise HTTPException(status_code=404, detail="Exam attempt not found")
    if attempt.llm_report is None:
        raise HTTPException(status_code=404, detail="Report not found")

    return LlmReportRead.from_model(attempt.llm_report)
