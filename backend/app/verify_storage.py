from __future__ import annotations

import json
from typing import Any

from .artifacts import get_artifact_store
from .database import SessionLocal
from .models import (
    Course,
    CourseEnrollment,
    CourseProfessor,
    Exam,
    ExamCourse,
    Problem,
    ProblemArtifact,
    Professor,
    SampleRunArtifact,
    Student,
    SubmissionArtifact,
    User,
)


def build_storage_report() -> dict[str, Any]:
    db = SessionLocal()
    try:
        table_counts = {
            "users": db.query(User).count(),
            "professors": db.query(Professor).count(),
            "students": db.query(Student).count(),
            "courses": db.query(Course).count(),
            "course_professors": db.query(CourseProfessor).count(),
            "course_enrollments": db.query(CourseEnrollment).count(),
            "exams": db.query(Exam).count(),
            "exam_courses": db.query(ExamCourse).count(),
            "problems": db.query(Problem).count(),
            "problem_artifacts": db.query(ProblemArtifact).count(),
            "submission_artifacts": db.query(SubmissionArtifact).count(),
            "sample_run_artifacts": db.query(SampleRunArtifact).count(),
        }
        exams_without_course = (
            db.query(Exam)
            .outerjoin(ExamCourse, ExamCourse.exam_id == Exam.id)
            .filter(ExamCourse.exam_id.is_(None))
            .count()
        )
        problems_without_active_artifact = (
            db.query(Problem)
            .outerjoin(
                ProblemArtifact,
                (ProblemArtifact.problem_id == Problem.id)
                & (ProblemArtifact.is_active == 1),
            )
            .filter(ProblemArtifact.id.is_(None))
            .count()
        )
        missing_object_keys = _missing_object_keys(
            [
                key
                for artifact in db.query(ProblemArtifact).all()
                for key in (artifact.statement_s3_key, artifact.testcases_s3_key)
            ]
            + [
                key
                for artifact in db.query(SubmissionArtifact).all()
                for key in (artifact.source_s3_key, artifact.result_s3_key)
                if key
            ]
            + [
                key
                for artifact in db.query(SampleRunArtifact).all()
                for key in (artifact.source_s3_key, artifact.result_s3_key)
                if key
            ]
        )
        ok = (
            exams_without_course == 0
            and problems_without_active_artifact == 0
            and not missing_object_keys
        )
        return {
            "ok": ok,
            "table_counts": table_counts,
            "exams_without_course": exams_without_course,
            "problems_without_active_artifact": problems_without_active_artifact,
            "missing_object_keys": missing_object_keys,
        }
    finally:
        db.close()


def _missing_object_keys(keys: list[str]) -> list[str]:
    store = get_artifact_store()
    return [key for key in keys if not store.exists(key)]


def main() -> None:
    report = build_storage_report()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["ok"] else 1)


if __name__ == "__main__":
    main()
