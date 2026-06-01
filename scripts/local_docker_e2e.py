from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = REPO_ROOT / "tmp"


def configure_environment(database_path: Path, sandbox_path: Path) -> None:
    os.environ["DATABASE_URL"] = f"sqlite:///{database_path.as_posix()}"
    os.environ["QUEUE_BACKEND"] = "local"
    os.environ["AUTO_CREATE_TABLES"] = "true"
    os.environ["AUTO_SEED"] = "true"
    os.environ["JUDGE_BASE_TMP_DIR"] = str(sandbox_path)


def main() -> None:
    os.chdir(REPO_ROOT)
    sys.path.insert(0, str(REPO_ROOT))
    RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
    run_root = Path(tempfile.mkdtemp(prefix="hufsolve-docker-e2e-", dir=RUNTIME_ROOT))
    configure_environment(
        database_path=run_root / "hufsolve.db",
        sandbox_path=run_root / "sandbox",
    )

    engine = None

    try:
        from fastapi.testclient import TestClient

        from backend.app.database import engine
        from backend.app.main import app
        from worker.main import process_message
        from worker.queue import LocalWorkerQueue

        queue = LocalWorkerQueue()

        with TestClient(app) as client:
            exams_response = client.get("/exams")
            exams_response.raise_for_status()
            problem_id = exams_response.json()[0]["problems"][0]["id"]

            sample_created = client.post(
                "/runs",
                json={
                    "problemId": problem_id,
                    "language": "python",
                    "sourceCode": "a, b = map(int, input().split())\nprint(a + b)",
                    "sampleIndex": 0,
                },
            )
            sample_created.raise_for_status()

            submission_created = client.post(
                "/submissions",
                json={
                    "problemId": problem_id,
                    "language": "python",
                    "sourceCode": "a, b = map(int, input().split())\nprint(a + b)",
                    "studentId": "local-docker-e2e",
                    "studentName": "Local Docker E2E",
                },
            )
            submission_created.raise_for_status()

            processed_types = []
            for _ in range(2):
                message = queue.receive()
                if message is None:
                    raise RuntimeError("Expected a pending worker message")

                processed_types.append(message.task_type)
                process_message(message)
                queue.ack(message)

            run_id = sample_created.json()["runId"]
            submission_id = submission_created.json()["submissionId"]
            sample_result = client.get(f"/runs/{run_id}")
            submission_result = client.get(f"/submissions/{submission_id}")
            sample_result.raise_for_status()
            submission_result.raise_for_status()

            summary = {
                "processed": processed_types,
                "sample": sample_result.json(),
                "submission": submission_result.json(),
            }

            if summary["processed"] != ["sample_run", "submission"]:
                raise RuntimeError(f"Unexpected worker order: {summary['processed']}")
            if summary["sample"]["status"] != "COMPLETED":
                raise RuntimeError(f"Sample run failed: {summary['sample']}")
            if summary["sample"]["stdout"].strip() != summary["sample"]["expectedOutput"].strip():
                raise RuntimeError(f"Sample output mismatch: {summary['sample']}")
            if summary["submission"]["status"] != "ACCEPTED":
                raise RuntimeError(f"Submission failed: {summary['submission']}")
            if summary["submission"]["score"] != 100:
                raise RuntimeError(f"Unexpected submission score: {summary['submission']}")

            print(json.dumps(summary, ensure_ascii=False, indent=2))
    finally:
        if engine is not None:
            engine.dispose()
        shutil.rmtree(run_root, ignore_errors=True)


if __name__ == "__main__":
    main()
