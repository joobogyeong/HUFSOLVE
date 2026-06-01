from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .models import Exam, ExamAttempt, Problem, SampleRun, Submission


class CamelModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class SampleCase(CamelModel):
    input: str
    output: str


class ProblemRead(CamelModel):
    id: int
    title: str
    level: Literal["Easy", "Medium", "Hard"]
    points: int
    time_limit_ms: int = Field(alias="timeLimitMs")
    memory_limit_mb: int = Field(alias="memoryLimitMb")
    description: list[str]
    input_description: str = Field(alias="inputDescription")
    output_description: str = Field(alias="outputDescription")
    constraints: list[str]
    samples: list[SampleCase]
    starter_code: str = Field(alias="starterCode")

    @classmethod
    def from_model(cls, problem: Problem) -> "ProblemRead":
        return cls(
            id=problem.id,
            title=problem.title,
            level=problem.level,
            points=problem.points,
            time_limit_ms=problem.time_limit_ms,
            memory_limit_mb=problem.memory_limit_mb,
            description=problem.description,
            input_description=problem.input_description,
            output_description=problem.output_description,
            constraints=problem.constraints,
            samples=[SampleCase(**sample) for sample in problem.samples],
            starter_code=problem.starter_code,
        )


class ExamRead(CamelModel):
    room_code: str = Field(alias="roomCode")
    title: str
    course: str
    professor: str
    exam_type: str = Field(alias="examType")
    duration_seconds: int = Field(alias="durationSeconds")
    starts_at: datetime = Field(alias="startsAt")
    problems: list[ProblemRead]

    @classmethod
    def from_model(cls, exam: Exam) -> "ExamRead":
        return cls(
            room_code=exam.room_code,
            title=exam.title,
            course=exam.course,
            professor=exam.professor,
            exam_type=exam.exam_type,
            duration_seconds=exam.duration_seconds,
            starts_at=exam.starts_at,
            problems=[ProblemRead.from_model(problem) for problem in exam.problems],
        )


class SubmissionCreate(CamelModel):
    problem_id: int = Field(alias="problemId")
    language: Literal["python"] = "python"
    source_code: str = Field(alias="sourceCode", min_length=1, max_length=100_000)
    student_id: str | None = Field(default=None, alias="studentId")
    student_name: str | None = Field(default=None, alias="studentName")


class SubmissionCreated(CamelModel):
    submission_id: int = Field(alias="submissionId")
    status: str


class SubmissionRead(CamelModel):
    submission_id: int = Field(alias="submissionId")
    problem_id: int = Field(alias="problemId")
    status: str
    score: int
    passed_cases: int = Field(alias="passedCases")
    total_cases: int = Field(alias="totalCases")
    runtime_ms: int | None = Field(alias="runtimeMs")
    memory_mb: int | None = Field(alias="memoryMb")
    message: str
    error_message: str | None = Field(alias="errorMessage")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    @classmethod
    def from_model(cls, submission: Submission) -> "SubmissionRead":
        return cls(
            submission_id=submission.id,
            problem_id=submission.problem_id,
            status=submission.status,
            score=submission.score,
            passed_cases=submission.passed_count,
            total_cases=submission.total_count,
            runtime_ms=submission.execution_time_ms,
            memory_mb=submission.memory_mb,
            message=_status_message(submission),
            error_message=submission.error_message,
            created_at=submission.created_at,
            updated_at=submission.updated_at,
        )


class SampleRunCreate(CamelModel):
    problem_id: int = Field(alias="problemId")
    language: Literal["python"] = "python"
    source_code: str = Field(alias="sourceCode", min_length=1, max_length=100_000)
    sample_index: int = Field(default=0, alias="sampleIndex", ge=0)


class SampleRunCreated(CamelModel):
    run_id: int = Field(alias="runId")
    status: str


class SampleRunRead(CamelModel):
    run_id: int = Field(alias="runId")
    problem_id: int = Field(alias="problemId")
    sample_index: int = Field(alias="sampleIndex")
    status: str
    input: str
    expected_output: str = Field(alias="expectedOutput")
    stdout: str | None
    stderr: str | None
    runtime_ms: int | None = Field(alias="runtimeMs")
    memory_mb: int | None = Field(alias="memoryMb")
    message: str
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")

    @classmethod
    def from_model(cls, sample_run: SampleRun) -> "SampleRunRead":
        return cls(
            run_id=sample_run.id,
            problem_id=sample_run.problem_id,
            sample_index=sample_run.sample_index,
            status=sample_run.status,
            input=sample_run.input_data,
            expected_output=sample_run.expected_output,
            stdout=sample_run.stdout,
            stderr=sample_run.stderr,
            runtime_ms=sample_run.execution_time_ms,
            memory_mb=sample_run.memory_mb,
            message=_sample_run_status_message(sample_run.status),
            created_at=sample_run.created_at,
            updated_at=sample_run.updated_at,
        )


class ExamAttemptCreate(CamelModel):
    room_code: str = Field(alias="roomCode", min_length=1)
    student_id: str = Field(alias="studentId", min_length=1)
    student_name: str = Field(alias="studentName", min_length=1)
    status: str = "최종 제출"


class ExamAttemptRead(CamelModel):
    id: str
    title: str
    room_code: str = Field(alias="roomCode")
    submitted_at: datetime = Field(alias="submittedAt")
    score: int
    passed_problems: int = Field(alias="passedProblems")
    total_problems: int = Field(alias="totalProblems")
    status: str

    @classmethod
    def from_model(cls, attempt: ExamAttempt) -> "ExamAttemptRead":
        return cls(
            id=f"history-{attempt.id}",
            title=attempt.exam.title,
            room_code=attempt.exam.room_code,
            submitted_at=attempt.submitted_at,
            score=attempt.score,
            passed_problems=attempt.passed_problems,
            total_problems=attempt.total_problems,
            status=attempt.status,
        )


def _status_message(submission: Submission) -> str:
    if submission.status == "PENDING":
        return "채점 대기열에 등록되었습니다."
    if submission.status == "RUNNING":
        return "Worker가 Docker sandbox에서 채점 중입니다."
    if submission.status == "ACCEPTED":
        return "모든 테스트케이스를 통과했습니다."
    if submission.status == "WRONG_ANSWER":
        return "일부 테스트케이스에서 예상 출력과 다른 값이 확인되었습니다."
    if submission.status == "TIME_LIMIT_EXCEEDED":
        return "시간 제한을 초과했습니다."
    if submission.status == "MEMORY_LIMIT_EXCEEDED":
        return "메모리 제한을 초과했습니다."
    if submission.status == "OUTPUT_LIMIT_EXCEEDED":
        return "출력 크기 제한을 초과했습니다."
    if submission.status == "RUNTIME_ERROR":
        return "코드 실행 중 오류가 발생했습니다."
    if submission.status == "SYSTEM_ERROR":
        return "채점 시스템 처리 중 오류가 발생했습니다."

    return submission.status


def _sample_run_status_message(status: str) -> str:
    if status == "PENDING":
        return "샘플 실행 대기열에 등록되었습니다."
    if status == "RUNNING":
        return "Worker가 Docker sandbox에서 샘플을 실행 중입니다."
    if status == "COMPLETED":
        return "샘플 실행이 완료되었습니다."
    if status == "TIME_LIMIT_EXCEEDED":
        return "샘플 실행 시간이 제한을 초과했습니다."
    if status == "MEMORY_LIMIT_EXCEEDED":
        return "샘플 실행 메모리가 제한을 초과했습니다."
    if status == "OUTPUT_LIMIT_EXCEEDED":
        return "샘플 실행 출력 크기가 제한을 초과했습니다."
    if status == "RUNTIME_ERROR":
        return "샘플 실행 중 런타임 오류가 발생했습니다."
    if status == "SYSTEM_ERROR":
        return "샘플 실행 시스템 처리 중 오류가 발생했습니다."

    return status
