from __future__ import annotations

import hashlib

from sqlalchemy.orm import Session

from .artifact_service import (
    active_problem_artifact,
    store_problem_artifact,
    store_sample_run_result,
    store_sample_run_source,
    store_submission_result,
    store_submission_source,
)
from .models import (
    Course,
    CourseEnrollment,
    CourseProfessor,
    Exam,
    ExamAttempt,
    ExamCourse,
    Problem,
    Professor,
    SampleRun,
    Student,
    Submission,
    Testcase,
    User,
)
from .seed_catalog import build_seed_exams


SEED_EXAMS = build_seed_exams()


def seed_database(db: Session) -> None:
    if db.query(Exam).first() is None:
        _seed_exams(db)

    synchronize_seed_problem_solutions(db)
    synchronize_reference_data(db)
    synchronize_problem_artifacts(db)
    synchronize_execution_artifacts(db)
    db.commit()


def synchronize_reference_data(db: Session) -> None:
    for exam in db.query(Exam).order_by(Exam.id.asc()).all():
        course = _get_or_create_course(db, exam)
        professor = _get_or_create_professor(db, exam.professor)

        if db.get(ExamCourse, exam.id) is None:
            db.add(ExamCourse(exam_id=exam.id, course_id=course.id))

        if db.get(CourseProfessor, (course.id, professor.id)) is None:
            db.add(CourseProfessor(course_id=course.id, professor_id=professor.id))
        db.flush()

    db.flush()

    attempt_rows = (
        db.query(ExamAttempt.exam_id, ExamAttempt.student_id, ExamAttempt.student_name).all()
    )
    submission_rows = (
        db.query(Submission.exam_id, Submission.student_id, Submission.student_name)
        .filter(Submission.student_id.is_not(None))
        .all()
    )
    for exam_id, student_number, student_name in [*attempt_rows, *submission_rows]:
        if not student_number:
            continue
        student = _get_or_create_student(db, student_number, student_name or student_number)
        exam_course = db.get(ExamCourse, exam_id)
        if exam_course is None:
            continue
        if db.get(CourseEnrollment, (exam_course.course_id, student.id)) is None:
            db.add(
                CourseEnrollment(
                    course_id=exam_course.course_id,
                    student_id=student.id,
                )
            )
            db.flush()


def synchronize_seed_problem_solutions(db: Session) -> None:
    solution_by_key = {
        (exam_data["room_code"], problem_data["title"]): problem_data.get(
            "reference_solution"
        )
        for exam_data in SEED_EXAMS
        for problem_data in exam_data["problems"]
    }
    for exam in db.query(Exam).order_by(Exam.id.asc()).all():
        for problem in exam.problems:
            solution = solution_by_key.get((exam.room_code, problem.title))
            if solution and not problem.reference_solution:
                problem.reference_solution = solution
    db.flush()


def synchronize_problem_artifacts(db: Session) -> None:
    for problem in db.query(Problem).order_by(Problem.id.asc()).all():
        if active_problem_artifact(problem) is None:
            store_problem_artifact(problem)


def synchronize_execution_artifacts(db: Session) -> None:
    for submission in db.query(Submission).order_by(Submission.id.asc()).all():
        if submission.artifact is None:
            store_submission_source(submission, submission.source_code)
        if submission.status not in {"PENDING", "RUNNING"} and not submission.artifact.result_s3_key:
            store_submission_result(
                submission,
                {
                    "submission_id": submission.id,
                    "problem_id": submission.problem_id,
                    "status": submission.status,
                    "score": submission.score,
                    "passed_count": submission.passed_count,
                    "total_count": submission.total_count,
                    "execution_time_ms": submission.execution_time_ms,
                    "error_message": submission.error_message,
                    "migrated_summary": True,
                },
            )

    for sample_run in db.query(SampleRun).order_by(SampleRun.id.asc()).all():
        if sample_run.artifact is None:
            store_sample_run_source(sample_run, sample_run.source_code)
        if sample_run.status not in {"PENDING", "RUNNING"} and not sample_run.artifact.result_s3_key:
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
                    "migrated_summary": True,
                },
            )


def enroll_student_for_exam(
    db: Session,
    exam: Exam,
    student_number: str,
    student_name: str,
) -> Student:
    student = _get_or_create_student(db, student_number, student_name)
    exam_course = db.get(ExamCourse, exam.id)
    if exam_course is None:
        course = _get_or_create_course(db, exam)
        exam_course = ExamCourse(exam_id=exam.id, course_id=course.id)
        db.add(exam_course)
        db.flush()

    if db.get(CourseEnrollment, (exam_course.course_id, student.id)) is None:
        db.add(
            CourseEnrollment(
                course_id=exam_course.course_id,
                student_id=student.id,
            )
        )
    return student


def _seed_exams(db: Session) -> None:
    for exam_data in SEED_EXAMS:
        problems = exam_data["problems"]
        exam_fields = {key: value for key, value in exam_data.items() if key != "problems"}
        exam = Exam(**exam_fields)
        db.add(exam)
        db.flush()

        for problem_data in problems:
            hidden_cases = problem_data["hidden_cases"]
            problem_fields = {
                key: value for key, value in problem_data.items() if key != "hidden_cases"
            }
            problem = Problem(exam_id=exam.id, **problem_fields)
            db.add(problem)
            db.flush()

            for sample in problem.samples:
                db.add(
                    Testcase(
                        problem_id=problem.id,
                        input_data=sample["input"],
                        expected_output=sample["output"],
                        is_hidden=0,
                    )
                )

            for hidden_case in hidden_cases:
                db.add(
                    Testcase(
                        problem_id=problem.id,
                        input_data=hidden_case["input"],
                        expected_output=hidden_case["output"],
                        is_hidden=1,
                    )
                )
        db.flush()


def _get_or_create_course(db: Session, exam: Exam) -> Course:
    academic_year = exam.starts_at.year
    semester = "1" if exam.starts_at.month <= 6 else "2"
    code = f"COURSE-{_stable_id(exam.course)}"
    course = (
        db.query(Course)
        .filter(
            Course.code == code,
            Course.academic_year == academic_year,
            Course.semester == semester,
        )
        .one_or_none()
    )
    if course is None:
        course = Course(
            code=code,
            name=exam.course,
            academic_year=academic_year,
            semester=semester,
        )
        db.add(course)
        db.flush()
    return course


def _get_or_create_professor(db: Session, name: str) -> Professor:
    employee_number = f"PROF-{_stable_id(name)}"
    professor = (
        db.query(Professor).filter(Professor.employee_number == employee_number).one_or_none()
    )
    if professor is None:
        user = User(
            username=f"professor-{_stable_id(name).lower()}",
            name=name,
            role="PROFESSOR",
        )
        professor = Professor(user=user, employee_number=employee_number)
        db.add(professor)
        db.flush()
    return professor


def _get_or_create_student(db: Session, student_number: str, name: str) -> Student:
    student = (
        db.query(Student).filter(Student.student_number == student_number).one_or_none()
    )
    if student is None:
        user = User(
            username=f"student-{student_number}",
            name=name,
            role="STUDENT",
        )
        student = Student(user=user, student_number=student_number)
        db.add(student)
        db.flush()
    return student


def _stable_id(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12].upper()
