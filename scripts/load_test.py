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

DEFAULT_SOURCE_CODE = "a, b = map(int, input().split())\nprint(a+b)\n"


@dataclass
class SubmissionMetric:
    ok: bool
    submission_id: int | None
    accepted_latency_ms: int | None
    completed_latency_ms: int | None
    final_status: str
    error: str | None = None


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
        while time.perf_counter() < deadline:
            status_response = await client.get(f"/submissions/{submission_id}")
            status_response.raise_for_status()
            payload = status_response.json()
            final_status = str(payload["status"])

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
            error="poll timeout",
        )

    except Exception as exc:
        return SubmissionMetric(
            ok=False,
            submission_id=None,
            accepted_latency_ms=None,
            completed_latency_ms=None,
            final_status="REQUEST_ERROR",
            error=str(exc),
        )


async def run_load_test(args: argparse.Namespace) -> dict[str, Any]:
    source_code = DEFAULT_SOURCE_CODE
    if args.source_file:
        with open(args.source_file, "r", encoding="utf-8") as source:
            source_code = source.read()

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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="HUFSOLVE submission burst load test")
    parser.add_argument("--api-base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--problem-id", type=int, default=1)
    parser.add_argument("--total", type=int, default=20)
    parser.add_argument("--concurrency", type=int, default=5)
    parser.add_argument("--source-file")
    parser.add_argument("--request-timeout", type=float, default=10.0)
    parser.add_argument("--poll-interval", type=float, default=1.0)
    parser.add_argument("--poll-timeout", type=float, default=120.0)
    parser.add_argument("--student-prefix", default="load")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = asyncio.run(run_load_test(args))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
