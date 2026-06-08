from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import time
from dataclasses import dataclass
from typing import Any

import httpx


TERMINAL_STATUSES = {
    "ACCEPTED",
    "WRONG_ANSWER",
    "TIME_LIMIT_EXCEEDED",
    "MEMORY_LIMIT_EXCEEDED",
    "OUTPUT_LIMIT_EXCEEDED",
    "RUNTIME_ERROR",
    "SYSTEM_ERROR",
}
TERMINAL_ATTEMPT_STATUSES = {"COMPLETED", "SYSTEM_ERROR"}

DEFAULT_SOURCE_CODE = "a, b = map(int, input().split())\nprint(a+b)\n"


@dataclass
class SubmissionMetric:
    ok: bool
    submission_id: int | None
    accepted_latency_ms: int | None
    completed_latency_ms: int | None
    final_status: str
    error: str | None = None


@dataclass
class ExamAttemptMetric:
    ok: bool
    attempt_id: int | None
    accepted_latency_ms: int | None
    completed_latency_ms: int | None
    final_status: str
    error: str | None = None


def format_error(exc: Exception) -> str:
    return f"{type(exc).__name__}: {exc!r}"


def percentile(values: list[int], pct: float) -> int | None:
    if not values:
        return None

    sorted_values = sorted(values)
    index = int((len(sorted_values) - 1) * pct)
    return sorted_values[index]


def summarize_latencies(values: list[int]) -> dict[str, int | None]:
    if not values:
        return {
            "min": None,
            "avg": None,
            "p50": None,
            "p95": None,
            "max": None,
        }

    return {
        "min": min(values),
        "avg": int(statistics.mean(values)),
        "p50": percentile(values, 0.50),
        "p95": percentile(values, 0.95),
        "max": max(values),
    }


async def submit_and_wait(
    client: httpx.AsyncClient,
    problem_id: int,
    source_code: str,
    poll_interval: float,
    poll_timeout: float,
    student_prefix: str,
    sequence: int,
) -> SubmissionMetric:
    start = time.perf_counter()

    try:
        response = await client.post(
            "/submissions",
            json={
                "problemId": problem_id,
                "language": "python",
                "sourceCode": source_code,
                "studentId": f"{student_prefix}-{sequence}",
                "studentName": f"load-tester-{sequence}",
            },
        )
        response.raise_for_status()
        accepted_latency_ms = int((time.perf_counter() - start) * 1000)
        created = response.json()
        submission_id = int(created["submissionId"])
        final_status = str(created["status"])

        deadline = time.perf_counter() + poll_timeout
        last_poll_error: str | None = None
        while time.perf_counter() < deadline:
            try:
                status_response = await client.get(f"/submissions/{submission_id}")
                status_response.raise_for_status()
                payload = status_response.json()
                final_status = str(payload["status"])
                last_poll_error = None
            except Exception as exc:
                last_poll_error = format_error(exc)
                await asyncio.sleep(poll_interval)
                continue

            if final_status in TERMINAL_STATUSES:
                completed_latency_ms = int((time.perf_counter() - start) * 1000)
                return SubmissionMetric(
                    ok=True,
                    submission_id=submission_id,
                    accepted_latency_ms=accepted_latency_ms,
                    completed_latency_ms=completed_latency_ms,
                    final_status=final_status,
                )

            await asyncio.sleep(poll_interval)

        return SubmissionMetric(
            ok=False,
            submission_id=submission_id,
            accepted_latency_ms=accepted_latency_ms,
            completed_latency_ms=None,
            final_status=final_status,
            error=f"poll timeout; last poll error={last_poll_error}",
        )

    except Exception as exc:
        return SubmissionMetric(
            ok=False,
            submission_id=None,
            accepted_latency_ms=None,
            completed_latency_ms=None,
            final_status="REQUEST_ERROR",
            error=format_error(exc),
        )


async def run_load_test(args: argparse.Namespace) -> dict[str, Any]:
    source_code = DEFAULT_SOURCE_CODE
    if args.source_file:
        with open(args.source_file, "r", encoding="utf-8") as source:
            source_code = source.read()

    if args.scenario == "exam":
        return await run_exam_attempt_load_test(args, source_code)

    limits = httpx.Limits(max_connections=args.concurrency * 2)
    timeout = httpx.Timeout(args.request_timeout)
    semaphore = asyncio.Semaphore(args.concurrency)

    async with httpx.AsyncClient(
        base_url=args.api_base_url.rstrip("/"),
        timeout=timeout,
        limits=limits,
    ) as client:
        started_at = time.perf_counter()

        async def guarded_submit(sequence: int) -> SubmissionMetric:
            async with semaphore:
                return await submit_and_wait(
                    client=client,
                    problem_id=args.problem_id,
                    source_code=source_code,
                    poll_interval=args.poll_interval,
                    poll_timeout=args.poll_timeout,
                    student_prefix=args.student_prefix,
                    sequence=sequence,
                )

        metrics = await asyncio.gather(
            *(guarded_submit(sequence) for sequence in range(1, args.total + 1))
        )
        elapsed_ms = int((time.perf_counter() - started_at) * 1000)

    accepted_latencies = [
        metric.accepted_latency_ms
        for metric in metrics
        if metric.accepted_latency_ms is not None
    ]
    completed_latencies = [
        metric.completed_latency_ms
        for metric in metrics
        if metric.completed_latency_ms is not None
    ]
    status_counts: dict[str, int] = {}
    errors: list[str] = []

    for metric in metrics:
        status_counts[metric.final_status] = status_counts.get(metric.final_status, 0) + 1
        if metric.error:
            errors.append(metric.error)

    return {
        "scenario": "submission",
        "apiBaseUrl": args.api_base_url,
        "problemId": args.problem_id,
        "total": args.total,
        "concurrency": args.concurrency,
        "elapsedMs": elapsed_ms,
        "successfulTerminalCount": sum(1 for metric in metrics if metric.ok),
        "failedOrTimedOutCount": sum(1 for metric in metrics if not metric.ok),
        "statusCounts": status_counts,
        "acceptedLatencyMs": summarize_latencies(accepted_latencies),
        "completedLatencyMs": summarize_latencies(completed_latencies),
        "sampleErrors": errors[:5],
    }


async def submit_exam_attempt_and_wait(
    client: httpx.AsyncClient,
    room_code: str,
    problems: list[dict[str, Any]],
    source_code: str,
    poll_interval: float,
    poll_timeout: float,
    student_prefix: str,
    sequence: int,
) -> ExamAttemptMetric:
    start = time.perf_counter()
    try:
        response = await client.post(
            "/exam-attempts",
            json={
                "roomCode": room_code,
                "studentId": f"{student_prefix}-{sequence}",
                "studentName": f"load-tester-{sequence}",
                "answers": [
                    {
                        "problemId": int(problem["id"]),
                        "language": "python",
                        "sourceCode": source_code,
                    }
                    for problem in problems
                ],
            },
        )
        response.raise_for_status()
        accepted_latency_ms = int((time.perf_counter() - start) * 1000)
        payload = response.json()
        attempt_id = int(payload["attemptId"])
        final_status = str(payload["status"])
        deadline = time.perf_counter() + poll_timeout

        while time.perf_counter() < deadline:
            result = await client.get(f"/exam-attempts/{attempt_id}")
            result.raise_for_status()
            final_status = str(result.json()["status"])
            if final_status in TERMINAL_ATTEMPT_STATUSES:
                return ExamAttemptMetric(
                    ok=True,
                    attempt_id=attempt_id,
                    accepted_latency_ms=accepted_latency_ms,
                    completed_latency_ms=int((time.perf_counter() - start) * 1000),
                    final_status=final_status,
                )
            await asyncio.sleep(poll_interval)

        return ExamAttemptMetric(
            ok=False,
            attempt_id=attempt_id,
            accepted_latency_ms=accepted_latency_ms,
            completed_latency_ms=None,
            final_status=final_status,
            error="poll timeout",
        )
    except Exception as exc:
        return ExamAttemptMetric(
            ok=False,
            attempt_id=None,
            accepted_latency_ms=None,
            completed_latency_ms=None,
            final_status="REQUEST_ERROR",
            error=format_error(exc),
        )


async def run_exam_attempt_load_test(
    args: argparse.Namespace,
    source_code: str,
) -> dict[str, Any]:
    limits = httpx.Limits(max_connections=args.concurrency * 2)
    timeout = httpx.Timeout(args.request_timeout)
    semaphore = asyncio.Semaphore(args.concurrency)

    async with httpx.AsyncClient(
        base_url=args.api_base_url.rstrip("/"),
        timeout=timeout,
        limits=limits,
    ) as client:
        exams_response = await client.get("/exams")
        exams_response.raise_for_status()
        exams = exams_response.json()
        exam = next(
            (item for item in exams if item["roomCode"] == args.room_code),
            None,
        )
        if exam is None:
            raise RuntimeError(f"Exam room code not found: {args.room_code}")

        started_at = time.perf_counter()

        async def guarded_submit(sequence: int) -> ExamAttemptMetric:
            async with semaphore:
                return await submit_exam_attempt_and_wait(
                    client=client,
                    room_code=args.room_code,
                    problems=exam["problems"],
                    source_code=source_code,
                    poll_interval=args.poll_interval,
                    poll_timeout=args.poll_timeout,
                    student_prefix=args.student_prefix,
                    sequence=sequence,
                )

        metrics = await asyncio.gather(
            *(guarded_submit(sequence) for sequence in range(1, args.total + 1))
        )
        elapsed_ms = int((time.perf_counter() - started_at) * 1000)

    attempt_ids = [metric.attempt_id for metric in metrics if metric.attempt_id is not None]
    status_counts: dict[str, int] = {}
    for metric in metrics:
        status_counts[metric.final_status] = status_counts.get(metric.final_status, 0) + 1

    return {
        "scenario": "exam",
        "apiBaseUrl": args.api_base_url,
        "roomCode": args.room_code,
        "total": args.total,
        "concurrency": args.concurrency,
        "elapsedMs": elapsed_ms,
        "successfulTerminalCount": sum(1 for metric in metrics if metric.ok),
        "failedOrTimedOutCount": sum(1 for metric in metrics if not metric.ok),
        "uniqueAttemptCount": len(set(attempt_ids)),
        "duplicateAttemptCount": len(attempt_ids) - len(set(attempt_ids)),
        "statusCounts": status_counts,
        "gradingAcceptedLatencyMs": summarize_latencies(
            [
                metric.accepted_latency_ms
                for metric in metrics
                if metric.accepted_latency_ms is not None
            ]
        ),
        "completedLatencyMs": summarize_latencies(
            [
                metric.completed_latency_ms
                for metric in metrics
                if metric.completed_latency_ms is not None
            ]
        ),
        "sampleErrors": [metric.error for metric in metrics if metric.error][:5],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="HUFSOLVE submission burst load test")
    parser.add_argument("--scenario", choices=["submission", "exam"], default="submission")
    parser.add_argument("--api-base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--problem-id", type=int, default=1)
    parser.add_argument("--total", type=int, default=20)
    parser.add_argument("--concurrency", type=int, default=5)
    parser.add_argument("--source-file")
    parser.add_argument("--request-timeout", type=float, default=30.0)
    parser.add_argument("--poll-interval", type=float, default=1.0)
    parser.add_argument("--poll-timeout", type=float, default=120.0)
    parser.add_argument("--student-prefix", default="load")
    parser.add_argument("--room-code", default="HUF-2026")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = asyncio.run(run_load_test(args))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
