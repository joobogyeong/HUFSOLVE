from __future__ import annotations

from backend.app.database import SessionLocal
from backend.app.llm_review import generate_report_payload
from backend.app.models import LlmReport


def generate_llm_report(report_id: int) -> None:
    db = SessionLocal()
    try:
        report = db.get(LlmReport, report_id)
        if report is None:
            raise RuntimeError(f"LLM report {report_id} not found")
        if report.status == "COMPLETED":
            return

        report.status = "RUNNING"
        report.error_message = None
        db.commit()

        payload = generate_report_payload(db, report)
        report.summary = payload["summary"]
        report.strengths = payload["strengths"]
        report.weaknesses = payload["weaknesses"]
        report.problem_reviews = payload["problemReviews"]
        report.improvement_plan = payload["improvementPlan"]
        report.status = "COMPLETED"
        db.commit()
    except Exception as exc:
        db.rollback()
        _mark_system_error(db, report_id, str(exc))
        raise
    finally:
        db.close()


def mark_llm_report_system_error(report_id: int, message: str) -> None:
    db = SessionLocal()
    try:
        _mark_system_error(db, report_id, message)
    finally:
        db.close()


def _mark_system_error(db, report_id: int, message: str) -> None:
    report = db.get(LlmReport, report_id)
    if report is None:
        return

    report.status = "SYSTEM_ERROR"
    report.error_message = message[:2000]
    db.commit()
