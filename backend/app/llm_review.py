from __future__ import annotations

import json
import re
from typing import Any

from sqlalchemy.orm import Session, joinedload

from .artifact_service import load_problem_statement, load_submission_source
from .config import settings
from .models import ExamAttempt, LlmReport, Submission


REPORT_SYSTEM_PROMPT = """
당신은 한국어로 피드백을 제공하는 프로그래밍 튜터입니다.
모든 리포트는 반드시 자연스러운 한국어로 작성합니다.
정답 코드, 완성 코드, 숨김 테스트케이스 추정 내용은 제공하지 않습니다.
학생이 다음에 무엇을 고치면 되는지 중심으로 간결하게 작성합니다.
반드시 JSON 객체만 반환합니다.
""".strip()


def generate_report_payload(db: Session, report: LlmReport) -> dict[str, Any]:
    attempt = _load_attempt(db, report.exam_attempt_id)
    submissions = _load_attempt_submissions(db, attempt)
    prompt = build_review_prompt(attempt, submissions)

    if not settings.llm_review_enabled:
        return build_fallback_report(attempt, submissions)

    return call_bedrock_review(prompt)


def build_review_prompt(
    attempt: ExamAttempt,
    submissions: list[Submission],
) -> str:
    payload = {
        "instruction": (
            "다음 입력에는 각 문제 정보, 내부 평가 기준으로만 사용할 정답 예시 코드, "
            "그리고 학생이 제출한 코드가 포함되어 있습니다. 정답 예시 코드를 출력에 복사하거나 "
            "완성 풀이로 제공하지 마세요. 제출 코드에 대한 간략한 코드 리뷰와 보완하면 좋은 부분을 "
            "중심으로 한국어 리포트를 작성하세요. submissions 배열의 각 항목은 한 학생의 "
            "studentProblemKey 기준으로 문제별 최신 제출 하나를 의미합니다. problemReviews에는 "
            "각 제출마다 하나씩 리뷰를 작성하세요."
        ),
        "requiredJsonShape": {
            "summary": "string",
            "strengths": ["string"],
            "weaknesses": ["string"],
            "problemReviews": [
                {
                    "problemId": "number",
                    "title": "string",
                    "status": "string",
                    "score": "number",
                    "feedback": "string",
                    "missingConcepts": ["string"],
                    "nextStep": "string",
                }
            ],
            "improvementPlan": ["string"],
        },
        "exam": {
            "title": attempt.exam.title,
            "roomCode": attempt.exam.room_code,
            "score": attempt.score,
            "passedProblems": attempt.passed_problems,
            "totalProblems": attempt.total_problems,
        },
        "submissions": [_submission_payload(submission) for submission in submissions],
    }
    return json.dumps(payload, ensure_ascii=False)


def call_bedrock_review(prompt: str) -> dict[str, Any]:
    import boto3

    client = boto3.client("bedrock-runtime", region_name=settings.aws_region)
    response = client.invoke_model(
        modelId=settings.bedrock_review_model_id,
        body=json.dumps(
            {
                "model": settings.bedrock_review_model_id,
                "messages": [
                    {"role": "system", "content": REPORT_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.2,
                "max_completion_tokens": settings.bedrock_review_max_output_tokens,
                "stream": False,
            }
        ),
    )
    response_body = json.loads(response["body"].read().decode("utf-8"))
    content = response_body["choices"][0]["message"]["content"]
    return parse_report_json(str(content))


def parse_report_json(content: str) -> dict[str, Any]:
    content = re.sub(r"<reasoning>.*?</reasoning>", "", content, flags=re.DOTALL).strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", content, flags=re.DOTALL)
    if fenced:
        content = fenced.group(1).strip()

    start = content.find("{")
    end = content.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("LLM response did not include a JSON object")

    payload = json.loads(content[start : end + 1])
    return normalize_report_payload(payload)


def normalize_report_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "summary": str(payload.get("summary", "")).strip(),
        "strengths": _string_list(payload.get("strengths")),
        "weaknesses": _string_list(payload.get("weaknesses")),
        "problemReviews": [
            {
                "problemId": int(item.get("problemId", item.get("problem_id", 0))),
                "title": str(item.get("title", "")).strip(),
                "status": str(item.get("status", "")).strip(),
                "score": int(item.get("score", 0)),
                "feedback": str(item.get("feedback", "")).strip(),
                "missingConcepts": _string_list(
                    item.get("missingConcepts", item.get("missing_concepts"))
                ),
                "nextStep": str(item.get("nextStep", item.get("next_step", ""))).strip(),
            }
            for item in payload.get("problemReviews", payload.get("problem_reviews", []))
            if isinstance(item, dict)
        ],
        "improvementPlan": _string_list(
            payload.get("improvementPlan", payload.get("improvement_plan"))
        ),
    }

# 베드락 연동 안되어있을때 나오는 것
def build_fallback_report(
    attempt: ExamAttempt,
    submissions: list[Submission],
) -> dict[str, Any]:
    missed_count = max(attempt.total_problems - attempt.passed_problems, 0)
    return {
        "summary": (
            f"{attempt.exam.title}에서 {attempt.total_problems}문제 중 "
            f"{attempt.passed_problems}문제를 통과했습니다. "
            "아래 피드백은 로컬 개발용 기본 리포트이며, Bedrock 연동 시 더 구체적으로 생성됩니다."
        ),
        "strengths": [
            "시험 제출 흐름을 완료했고 채점 결과를 확인할 수 있습니다.",
            "통과한 문제에서는 요구된 출력 형식을 맞췄습니다.",
        ],
        "weaknesses": (
            ["오답 또는 미통과 문제의 경계 조건과 시간 복잡도를 다시 점검해야 합니다."]
            if missed_count
            else ["정답을 받은 코드도 함수 분리와 가독성을 한 번 더 점검하면 좋습니다."]
        ),
        "problemReviews": [
            _fallback_problem_review(submission) for submission in submissions
        ],
        "improvementPlan": [
            "오답 문제는 실패할 수 있는 반례를 먼저 직접 만들어보세요.",
            "입력 크기를 기준으로 시간 복잡도를 추정한 뒤 풀이를 다시 점검하세요.",
            "정답 코드는 변수명과 함수 분리를 개선하며 다시 작성해보세요.",
        ],
    }


def _load_attempt(db: Session, attempt_id: int) -> ExamAttempt:
    attempt = (
        db.query(ExamAttempt)
        .options(joinedload(ExamAttempt.exam))
        .filter(ExamAttempt.id == attempt_id)
        .one_or_none()
    )
    if attempt is None:
        raise RuntimeError(f"Exam attempt {attempt_id} not found")
    return attempt


def _load_attempt_submissions(db: Session, attempt: ExamAttempt) -> list[Submission]:
    previous_attempt = (
        db.query(ExamAttempt)
        .filter(
            ExamAttempt.exam_id == attempt.exam_id,
            ExamAttempt.student_id == attempt.student_id,
            ExamAttempt.id < attempt.id,
        )
        .order_by(ExamAttempt.submitted_at.desc(), ExamAttempt.id.desc())
        .first()
    )
    base_filters = [
        Submission.exam_id == attempt.exam_id,
        Submission.student_id == attempt.student_id,
    ]
    if previous_attempt is not None:
        base_filters.append(Submission.created_at > previous_attempt.submitted_at)

    query = (
        db.query(Submission)
        .options(joinedload(Submission.problem), joinedload(Submission.artifact))
        .filter(*base_filters, Submission.created_at <= attempt.submitted_at)
    )
    submissions = query.order_by(
        Submission.problem_id.asc(),
        Submission.created_at.desc(),
        Submission.id.desc(),
    ).all()
    if submissions:
        return _latest_submission_per_problem(submissions)

    # SQLite server timestamps can tie or drift slightly in fast tests. If the
    # strict upper bound yields nothing, still generate a report from this
    # attempt window instead of returning an empty LLM context.
    return (
        db.query(Submission)
        .options(joinedload(Submission.problem), joinedload(Submission.artifact))
        .filter(*base_filters)
        .order_by(
            Submission.problem_id.asc(),
            Submission.created_at.desc(),
            Submission.id.desc(),
        )
        .all()
    )
    return _latest_submission_per_problem(submissions)


def _submission_payload(submission: Submission) -> dict[str, Any]:
    statement = load_problem_statement(submission.problem)
    return {
        "studentProblemKey": f"{submission.student_id or 'anonymous'}_{submission.problem_id}",
        "problemId": submission.problem_id,
        "title": submission.problem.title,
        "status": submission.status,
        "score": submission.score,
        "passedCases": submission.passed_count,
        "totalCases": submission.total_count,
        "runtimeMs": submission.execution_time_ms,
        "errorMessage": submission.error_message,
        "problem": {
            "description": statement["description"],
            "inputDescription": statement["input_description"],
            "outputDescription": statement["output_description"],
            "constraints": statement["constraints"],
            "samples": statement["samples"],
        },
        "referenceSolutionCode": str(statement.get("reference_solution") or ""),
        "submittedCode": load_submission_source(submission)[
            : settings.bedrock_review_max_source_chars
        ],
    }


def _latest_submission_per_problem(submissions: list[Submission]) -> list[Submission]:
    latest_by_problem: dict[int, Submission] = {}
    for submission in submissions:
        if submission.problem_id not in latest_by_problem:
            latest_by_problem[submission.problem_id] = submission

    return [
        latest_by_problem[problem_id]
        for problem_id in sorted(latest_by_problem)
    ]

# 베드락 연동 안되어있을때 나오는것
def _fallback_problem_review(submission: Submission) -> dict[str, Any]:
    accepted = submission.status == "ACCEPTED"
    return {
        "problemId": submission.problem_id,
        "title": submission.problem.title,
        "status": submission.status,
        "score": submission.score,
        "feedback": (
            "채점 결과가 안정적입니다. 같은 풀이를 더 읽기 쉬운 구조로 정리해보세요."
            if accepted
            else "현재 제출은 일부 테스트를 통과하지 못했습니다. 입력 범위, 경계 조건, 반복 계산을 중심으로 다시 점검해보세요."
        ),
        "missingConcepts": (
            ["코드 가독성", "함수 분리"]
            if accepted
            else ["경계 조건", "시간 복잡도", "반례 만들기"]
        ),
        "nextStep": (
            "풀이를 함수 단위로 나누고 변수명을 더 명확하게 바꿔보세요."
            if accepted
            else "작은 반례를 직접 만든 뒤, 어떤 조건에서 출력이 달라지는지 추적해보세요."
        ),
    }


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]
