from __future__ import annotations

import hashlib
from datetime import datetime

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


def _starter(lines: list[str]) -> str:
    return "\n".join(lines) + "\n"


SEED_EXAMS = [
    {
        "room_code": "HUF-2026",
        "title": "클라우드 컴퓨팅 실습 평가",
        "course": "Cloud Computing",
        "professor": "김하늘",
        "exam_type": "중간고사",
        "duration_seconds": 60 * 75,
        "starts_at": datetime.fromisoformat("2026-06-03T09:00:00+09:00"),
        "problems": [
            {
                "title": "A+B 자동 채점",
                "level": "Easy",
                "points": 15,
                "description": [
                    "두 정수 A와 B를 입력받아 합을 출력하세요.",
                    "표준 입력으로 주어진 값을 읽고, 정답은 표준 출력으로만 출력해야 합니다.",
                ],
                "input_description": "첫째 줄에 정수 A와 B가 공백으로 구분되어 주어집니다.",
                "output_description": "A+B의 값을 한 줄에 출력합니다.",
                "constraints": ["-1,000 <= A, B <= 1,000", "불필요한 문장은 출력하지 않습니다."],
                "samples": [
                    {"input": "1 2", "output": "3"},
                    {"input": "-4 9", "output": "5"},
                ],
                "starter_code": _starter(
                    ["a, b = map(int, input().split())", "# TODO: 두 수의 합을 출력하세요."]
                ),
                "time_limit_ms": 2000,
                "memory_limit_mb": 128,
                "hidden_cases": [
                    {"input": "1000 -7", "output": "993"},
                    {"input": "0 0", "output": "0"},
                ],
            },
            {
                "title": "최댓값 찾기",
                "level": "Easy",
                "points": 15,
                "description": [
                    "정수 배열이 주어졌을 때 가장 큰 값을 출력하세요.",
                    "배열의 길이는 첫 줄에 주어지고, 둘째 줄에 배열 원소가 주어집니다.",
                ],
                "input_description": "첫째 줄에 N, 둘째 줄에 N개의 정수가 주어집니다.",
                "output_description": "배열에서 가장 큰 정수를 출력합니다.",
                "constraints": ["1 <= N <= 100,000", "-10^9 <= 각 원소 <= 10^9"],
                "samples": [{"input": "5\n3 1 9 2 7", "output": "9"}],
                "starter_code": _starter(
                    [
                        "n = int(input())",
                        "arr = list(map(int, input().split()))",
                        "# TODO: 최댓값을 출력하세요.",
                    ]
                ),
                "time_limit_ms": 2000,
                "memory_limit_mb": 128,
                "hidden_cases": [
                    {"input": "1\n-10", "output": "-10"},
                    {"input": "4\n4 4 4 4", "output": "4"},
                ],
            },
            {
                "title": "요청 로그 집계",
                "level": "Medium",
                "points": 20,
                "description": [
                    "API 서버 로그에서 성공 응답의 개수를 집계하세요.",
                    "각 로그는 HTTP status code 하나로 표현되며, 200 이상 300 미만이면 성공입니다.",
                ],
                "input_description": "첫째 줄에 로그 수 N, 다음 N줄에 status code가 주어집니다.",
                "output_description": "성공 응답의 개수를 출력합니다.",
                "constraints": ["1 <= N <= 200,000", "100 <= status code <= 599"],
                "samples": [{"input": "6\n200\n201\n404\n500\n204\n302", "output": "3"}],
                "starter_code": _starter(
                    [
                        "n = int(input())",
                        "count = 0",
                        "for _ in range(n):",
                        "    status = int(input())",
                        "    # TODO: 성공 응답을 세어보세요.",
                        "print(count)",
                    ]
                ),
                "time_limit_ms": 3000,
                "memory_limit_mb": 256,
                "hidden_cases": [
                    {"input": "3\n100\n199\n300", "output": "0"},
                    {"input": "4\n299\n200\n250\n500", "output": "3"},
                ],
            },
        ],
    },
    {
        "room_code": "ALG-MID",
        "title": "알고리즘 문제 해결 중간평가",
        "course": "Algorithm",
        "professor": "이서준",
        "exam_type": "중간고사",
        "duration_seconds": 60 * 90,
        "starts_at": datetime.fromisoformat("2026-06-05T13:30:00+09:00"),
        "problems": [
            {
                "title": "올바른 괄호",
                "level": "Easy",
                "points": 15,
                "description": [
                    "괄호 문자열이 올바른지 판별하세요.",
                    "열린 괄호는 반드시 나중에 등장하는 닫힌 괄호와 짝을 이루어야 합니다.",
                ],
                "input_description": "한 줄에 괄호 문자열 S가 주어집니다.",
                "output_description": "올바른 괄호 문자열이면 YES, 아니면 NO를 출력합니다.",
                "constraints": ["1 <= |S| <= 200,000", "S는 '('와 ')'로만 구성됩니다."],
                "samples": [
                    {"input": "(()())", "output": "YES"},
                    {"input": "())(", "output": "NO"},
                ],
                "starter_code": _starter(["s = input().strip()", "# TODO: 올바른 괄호인지 출력하세요."]),
                "time_limit_ms": 2000,
                "memory_limit_mb": 128,
                "hidden_cases": [
                    {"input": "(", "output": "NO"},
                    {"input": "()()()", "output": "YES"},
                ],
            },
            {
                "title": "회의실 배정",
                "level": "Medium",
                "points": 20,
                "description": [
                    "시작 시각과 종료 시각이 주어진 회의 중 겹치지 않게 선택할 수 있는 최대 개수를 구하세요.",
                    "한 회의가 끝나는 시각에 다른 회의를 바로 시작할 수 있습니다.",
                ],
                "input_description": "첫째 줄에 N, 다음 N줄에 시작 시각과 종료 시각이 주어집니다.",
                "output_description": "선택 가능한 회의의 최대 개수를 출력합니다.",
                "constraints": ["1 <= N <= 100,000", "0 <= 시작 < 종료 <= 10^9"],
                "samples": [{"input": "4\n1 3\n2 4\n3 5\n0 7", "output": "2"}],
                "starter_code": _starter(
                    [
                        "n = int(input())",
                        "meetings = [tuple(map(int, input().split())) for _ in range(n)]",
                        "# TODO: 최대 회의 수를 출력하세요.",
                    ]
                ),
                "time_limit_ms": 3000,
                "memory_limit_mb": 256,
                "hidden_cases": [
                    {"input": "3\n1 2\n2 3\n3 4", "output": "3"},
                    {"input": "2\n1 10\n2 3", "output": "1"},
                ],
            },
        ],
    },
]


def seed_database(db: Session) -> None:
    if db.query(Exam).first() is None:
        _seed_exams(db)

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
