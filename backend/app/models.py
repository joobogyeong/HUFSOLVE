from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    role: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    professor: Mapped["Professor | None"] = relationship(back_populates="user")
    student: Mapped["Student | None"] = relationship(back_populates="user")


class Professor(Base):
    __tablename__ = "professors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    employee_number: Mapped[str] = mapped_column(String(64), unique=True, index=True)

    user: Mapped["User"] = relationship(back_populates="professor")
    course_assignments: Mapped[list["CourseProfessor"]] = relationship(
        back_populates="professor",
        cascade="all, delete-orphan",
    )


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    student_number: Mapped[str] = mapped_column(String(64), unique=True, index=True)

    user: Mapped["User"] = relationship(back_populates="student")
    enrollments: Mapped[list["CourseEnrollment"]] = relationship(
        back_populates="student",
        cascade="all, delete-orphan",
    )


class Course(Base):
    __tablename__ = "courses"
    __table_args__ = (
        UniqueConstraint("code", "academic_year", "semester", name="uq_course_term"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    academic_year: Mapped[int] = mapped_column(Integer, nullable=False)
    semester: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    professor_assignments: Mapped[list["CourseProfessor"]] = relationship(
        back_populates="course",
        cascade="all, delete-orphan",
    )
    enrollments: Mapped[list["CourseEnrollment"]] = relationship(
        back_populates="course",
        cascade="all, delete-orphan",
    )
    exam_links: Mapped[list["ExamCourse"]] = relationship(
        back_populates="course",
        cascade="all, delete-orphan",
    )


class CourseProfessor(Base):
    __tablename__ = "course_professors"

    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), primary_key=True)
    professor_id: Mapped[int] = mapped_column(ForeignKey("professors.id"), primary_key=True)
    assignment_role: Mapped[str] = mapped_column(
        String(32),
        default="INSTRUCTOR",
        nullable=False,
    )

    course: Mapped["Course"] = relationship(back_populates="professor_assignments")
    professor: Mapped["Professor"] = relationship(back_populates="course_assignments")


class CourseEnrollment(Base):
    __tablename__ = "course_enrollments"

    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), primary_key=True)
    status: Mapped[str] = mapped_column(String(32), default="ENROLLED", nullable=False)
    enrolled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    course: Mapped["Course"] = relationship(back_populates="enrollments")
    student: Mapped["Student"] = relationship(back_populates="enrollments")


class Exam(Base):
    __tablename__ = "exams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    room_code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    course: Mapped[str] = mapped_column(String(255), nullable=False)
    professor: Mapped[str] = mapped_column(String(100), nullable=False)
    exam_type: Mapped[str] = mapped_column(String(50), nullable=False)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    problems: Mapped[list["Problem"]] = relationship(
        back_populates="exam",
        cascade="all, delete-orphan",
        order_by="Problem.id",
    )
    attempts: Mapped[list["ExamAttempt"]] = relationship(back_populates="exam")
    course_link: Mapped["ExamCourse | None"] = relationship(
        back_populates="exam",
        cascade="all, delete-orphan",
    )


class ExamCourse(Base):
    __tablename__ = "exam_courses"

    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id"), primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), index=True)

    exam: Mapped["Exam"] = relationship(back_populates="course_link")
    course: Mapped["Course"] = relationship(back_populates="exam_links")


class Problem(Base):
    __tablename__ = "problems"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id"), index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    level: Mapped[str] = mapped_column(String(32), nullable=False)
    points: Mapped[int] = mapped_column(Integer, nullable=False)
    time_limit_ms: Mapped[int] = mapped_column(Integer, default=2000, nullable=False)
    memory_limit_mb: Mapped[int] = mapped_column(Integer, default=128, nullable=False)
    description: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    input_description: Mapped[str] = mapped_column(Text, nullable=False)
    output_description: Mapped[str] = mapped_column(Text, nullable=False)
    constraints: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    samples: Mapped[list[dict[str, str]]] = mapped_column(JSON, nullable=False)
    starter_code: Mapped[str] = mapped_column(Text, nullable=False)
    reference_solution: Mapped[str | None] = mapped_column(Text, nullable=True)

    exam: Mapped["Exam"] = relationship(back_populates="problems")
    testcases: Mapped[list["Testcase"]] = relationship(
        back_populates="problem",
        cascade="all, delete-orphan",
        order_by="Testcase.id",
    )
    submissions: Mapped[list["Submission"]] = relationship(back_populates="problem")
    sample_runs: Mapped[list["SampleRun"]] = relationship(back_populates="problem")
    artifacts: Mapped[list["ProblemArtifact"]] = relationship(
        back_populates="problem",
        cascade="all, delete-orphan",
        order_by="ProblemArtifact.version.desc()",
    )


class Testcase(Base):
    __tablename__ = "testcases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    problem_id: Mapped[int] = mapped_column(ForeignKey("problems.id"), index=True)
    input_data: Mapped[str] = mapped_column(Text, nullable=False)
    expected_output: Mapped[str] = mapped_column(Text, nullable=False)
    is_hidden: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    score_weight: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    problem: Mapped["Problem"] = relationship(back_populates="testcases")


class ProblemArtifact(Base):
    __tablename__ = "problem_artifacts"
    __table_args__ = (
        UniqueConstraint("problem_id", "version", name="uq_problem_artifact_version"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    problem_id: Mapped[int] = mapped_column(ForeignKey("problems.id"), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    statement_s3_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    testcases_s3_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    statement_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    testcases_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    is_active: Mapped[int] = mapped_column(Integer, default=1, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    problem: Mapped["Problem"] = relationship(back_populates="artifacts")


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    exam_attempt_id: Mapped[int | None] = mapped_column(
        ForeignKey("exam_attempts.id"),
        index=True,
        nullable=True,
    )
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id"), index=True)
    problem_id: Mapped[int] = mapped_column(ForeignKey("problems.id"), index=True)
    student_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    student_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    language: Mapped[str] = mapped_column(String(32), default="python", nullable=False)
    source_code: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="PENDING", index=True)
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    passed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    execution_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    memory_mb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    problem: Mapped["Problem"] = relationship(back_populates="submissions")
    exam_attempt: Mapped["ExamAttempt | None"] = relationship(back_populates="submissions")
    artifact: Mapped["SubmissionArtifact | None"] = relationship(
        back_populates="submission",
        cascade="all, delete-orphan",
    )


class SubmissionArtifact(Base):
    __tablename__ = "submission_artifacts"

    submission_id: Mapped[int] = mapped_column(ForeignKey("submissions.id"), primary_key=True)
    source_s3_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    source_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    result_s3_key: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    submission: Mapped["Submission"] = relationship(back_populates="artifact")


class SampleRun(Base):
    __tablename__ = "sample_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    problem_id: Mapped[int] = mapped_column(ForeignKey("problems.id"), index=True)
    language: Mapped[str] = mapped_column(String(32), default="python", nullable=False)
    source_code: Mapped[str] = mapped_column(Text, nullable=False)
    sample_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    input_data: Mapped[str] = mapped_column(Text, nullable=False)
    expected_output: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="PENDING", index=True)
    stdout: Mapped[str | None] = mapped_column(Text, nullable=True)
    stderr: Mapped[str | None] = mapped_column(Text, nullable=True)
    execution_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    memory_mb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    problem: Mapped["Problem"] = relationship(back_populates="sample_runs")
    artifact: Mapped["SampleRunArtifact | None"] = relationship(
        back_populates="sample_run",
        cascade="all, delete-orphan",
    )


class SampleRunArtifact(Base):
    __tablename__ = "sample_run_artifacts"

    sample_run_id: Mapped[int] = mapped_column(ForeignKey("sample_runs.id"), primary_key=True)
    source_s3_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    source_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    result_s3_key: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    sample_run: Mapped["SampleRun"] = relationship(back_populates="artifact")


class ExamAttempt(Base):
    __tablename__ = "exam_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    finalization_key: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id"), index=True)
    student_id: Mapped[str] = mapped_column(String(64), index=True)
    student_name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    passed_problems: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_problems: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    exam: Mapped["Exam"] = relationship(back_populates="attempts")
    submissions: Mapped[list["Submission"]] = relationship(back_populates="exam_attempt")
    llm_report: Mapped["LlmReport | None"] = relationship(
        back_populates="exam_attempt",
        cascade="all, delete-orphan",
    )


class LlmReport(Base):
    __tablename__ = "llm_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    exam_attempt_id: Mapped[int] = mapped_column(
        ForeignKey("exam_attempts.id"),
        unique=True,
        index=True,
    )
    student_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    language: Mapped[str] = mapped_column(String(16), default="ko", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="PENDING", index=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    strengths: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    weaknesses: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    problem_reviews: Mapped[list[dict[str, object]] | None] = mapped_column(JSON, nullable=True)
    improvement_plan: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    model_id: Mapped[str] = mapped_column(String(128), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    exam_attempt: Mapped["ExamAttempt"] = relationship(back_populates="llm_report")


class EmailVerification(Base):
    __tablename__ = "email_verifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    student_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    student_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    code: Mapped[str] = mapped_column(String(10), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    verified: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
