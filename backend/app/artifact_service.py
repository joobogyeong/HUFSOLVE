from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .artifacts import get_json, get_text, put_json, put_text
from .models import (
    Problem,
    ProblemArtifact,
    SampleRun,
    SampleRunArtifact,
    Submission,
    SubmissionArtifact,
)


def store_submission_source(submission: Submission, source_code: str) -> SubmissionArtifact:
    key = _execution_key("submissions", submission.id, "source.py")
    source_key, source_hash = put_text(key, source_code)
    artifact = SubmissionArtifact(
        submission_id=submission.id,
        source_s3_key=source_key,
        source_sha256=source_hash,
    )
    submission.source_code = _artifact_reference(source_key)
    submission.artifact = artifact
    return artifact


def load_submission_source(submission: Submission) -> str:
    if submission.artifact is not None:
        return get_text(submission.artifact.source_s3_key)
    return submission.source_code


def store_sample_run_source(sample_run: SampleRun, source_code: str) -> SampleRunArtifact:
    key = _execution_key("sample-runs", sample_run.id, "source.py")
    source_key, source_hash = put_text(key, source_code)
    artifact = SampleRunArtifact(
        sample_run_id=sample_run.id,
        source_s3_key=source_key,
        source_sha256=source_hash,
    )
    sample_run.source_code = _artifact_reference(source_key)
    sample_run.artifact = artifact
    return artifact


def load_sample_run_source(sample_run: SampleRun) -> str:
    if sample_run.artifact is not None:
        return get_text(sample_run.artifact.source_s3_key)
    return sample_run.source_code


def store_submission_result(submission: Submission, result: dict[str, Any]) -> str:
    artifact = submission.artifact
    if artifact is None:
        artifact = store_submission_source(submission, submission.source_code)

    key = _execution_key("submissions", submission.id, "result.json")
    result_key, _ = put_json(key, result)
    artifact.result_s3_key = result_key
    return result_key


def store_sample_run_result(sample_run: SampleRun, result: dict[str, Any]) -> str:
    artifact = sample_run.artifact
    if artifact is None:
        artifact = store_sample_run_source(sample_run, sample_run.source_code)

    key = _execution_key("sample-runs", sample_run.id, "result.json")
    result_key, _ = put_json(key, result)
    artifact.result_s3_key = result_key
    return result_key


def load_problem_statement(problem: Problem) -> dict[str, Any]:
    artifact = active_problem_artifact(problem)
    if artifact is not None:
        statement = get_json(artifact.statement_s3_key)
        if not isinstance(statement, dict):
            raise RuntimeError(f"Invalid statement artifact for problem {problem.id}")
        return statement

    return problem_statement_payload(problem)


def load_problem_testcases(problem: Problem) -> list[dict[str, Any]]:
    artifact = active_problem_artifact(problem)
    if artifact is not None:
        testcases = get_json(artifact.testcases_s3_key)
        if not isinstance(testcases, list):
            raise RuntimeError(f"Invalid testcase artifact for problem {problem.id}")
        return testcases

    return problem_testcase_payload(problem)


def active_problem_artifact(problem: Problem) -> ProblemArtifact | None:
    return next((artifact for artifact in problem.artifacts if artifact.is_active), None)


def problem_statement_payload(problem: Problem) -> dict[str, Any]:
    return {
        "description": problem.description,
        "input_description": problem.input_description,
        "output_description": problem.output_description,
        "constraints": problem.constraints,
        "samples": problem.samples,
        "starter_code": problem.starter_code,
    }


def problem_testcase_payload(problem: Problem) -> list[dict[str, Any]]:
    return [
        {
            "id": testcase.id,
            "input": testcase.input_data,
            "expected_output": testcase.expected_output,
            "is_hidden": bool(testcase.is_hidden),
            "score_weight": testcase.score_weight,
        }
        for testcase in problem.testcases
    ]


def store_problem_artifact(problem: Problem, version: int = 1) -> ProblemArtifact:
    statement_key = f"problems/{problem.id}/versions/{version}/statement.json"
    testcases_key = f"problems/{problem.id}/versions/{version}/testcases.json"
    stored_statement_key, statement_hash = put_json(
        statement_key,
        problem_statement_payload(problem),
    )
    stored_testcases_key, testcases_hash = put_json(
        testcases_key,
        problem_testcase_payload(problem),
    )
    artifact = ProblemArtifact(
        problem_id=problem.id,
        version=version,
        statement_s3_key=stored_statement_key,
        testcases_s3_key=stored_testcases_key,
        statement_sha256=statement_hash,
        testcases_sha256=testcases_hash,
        is_active=1,
    )
    problem.artifacts.append(artifact)
    return artifact


def _execution_key(prefix: str, resource_id: int, filename: str) -> str:
    now = datetime.now(UTC)
    return f"{prefix}/{now:%Y/%m}/{resource_id}/{filename}"


def _artifact_reference(key: str) -> str:
    return f"[artifact:{key}]"
