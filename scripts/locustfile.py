from __future__ import annotations

import os
import time
from uuid import uuid4

from locust import HttpUser, constant, task
from locust.exception import StopUser


TERMINAL_STATUSES = {
    "ACCEPTED",
    "WRONG_ANSWER",
    "TIME_LIMIT_EXCEEDED",
    "MEMORY_LIMIT_EXCEEDED",
    "OUTPUT_LIMIT_EXCEEDED",
    "RUNTIME_ERROR",
    "SYSTEM_ERROR",
}

PROBLEM_ID = int(os.environ.get("HUFSOLVE_PROBLEM_ID", "1"))
POLL_INTERVAL_SECONDS = float(os.environ.get("HUFSOLVE_POLL_INTERVAL_SECONDS", "1"))
POLL_TIMEOUT_SECONDS = float(os.environ.get("HUFSOLVE_POLL_TIMEOUT_SECONDS", "600"))
SOURCE_CODE = os.environ.get(
    "HUFSOLVE_SOURCE_CODE",
    "while True:\n    pass\n",
)


class BurstSubmissionUser(HttpUser):
    wait_time = constant(POLL_INTERVAL_SECONDS)

    def on_start(self) -> None:
        unique_id = uuid4().hex
        self.submission_id: int | None = None
        self.submitted_at = time.perf_counter()

        with self.client.post(
            "/submissions",
            json={
                "problemId": PROBLEM_ID,
                "language": "python",
                "sourceCode": SOURCE_CODE,
                "studentId": f"locust-{unique_id}",
                "studentName": f"locust-{unique_id[:12]}",
            },
            name="POST /submissions",
            catch_response=True,
        ) as response:
            if response.status_code != 202:
                response.failure(f"expected 202, got {response.status_code}: {response.text}")
                raise StopUser()

            try:
                self.submission_id = int(response.json()["submissionId"])
            except (KeyError, TypeError, ValueError) as exc:
                response.failure(f"invalid submission response: {exc}")
                raise StopUser() from exc

    @task
    def poll_submission(self) -> None:
        if self.submission_id is None:
            raise StopUser()

        with self.client.get(
            f"/submissions/{self.submission_id}",
            name="GET /submissions/:submissionId",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"expected 200, got {response.status_code}: {response.text}")
                return

            try:
                status = response.json()["status"]
            except (KeyError, TypeError, ValueError) as exc:
                response.failure(f"invalid status response: {exc}")
                return

            if status in TERMINAL_STATUSES:
                raise StopUser()

            elapsed_seconds = time.perf_counter() - self.submitted_at
            if elapsed_seconds > POLL_TIMEOUT_SECONDS:
                response.failure(
                    f"poll timeout after {elapsed_seconds:.1f}s; last status={status}"
                )
                raise StopUser()
