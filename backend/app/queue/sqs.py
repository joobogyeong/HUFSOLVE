from __future__ import annotations

import json

from ..config import settings


class SqsQueueClient:
    def __init__(self) -> None:
        if not settings.sqs_queue_url:
            raise RuntimeError("SQS_QUEUE_URL is required when QUEUE_BACKEND=sqs")

        import boto3

        self._client = boto3.client("sqs", region_name=settings.aws_region)

    def enqueue_submission(self, submission_id: int) -> None:
        failed_ids = self.enqueue_submissions([submission_id])
        if failed_ids:
            raise RuntimeError(f"Failed to enqueue submissions: {failed_ids}")

    def enqueue_submissions(self, submission_ids: list[int]) -> list[int]:
        failed_ids: list[int] = []
        for offset in range(0, len(submission_ids), 10):
            chunk = submission_ids[offset : offset + 10]
            entries = [
                {
                    "Id": str(index),
                    "MessageBody": json.dumps({"submission_id": submission_id}),
                }
                for index, submission_id in enumerate(chunk)
            ]
            try:
                response = self._client.send_message_batch(
                    QueueUrl=settings.sqs_queue_url,
                    Entries=entries,
                )
            except Exception:
                failed_ids.extend(chunk)
                continue

            failed_entry_ids = {
                str(entry["Id"]) for entry in response.get("Failed", [])
            }
            failed_ids.extend(
                submission_id
                for index, submission_id in enumerate(chunk)
                if str(index) in failed_entry_ids
            )

        return failed_ids

    def enqueue_sample_run(self, sample_run_id: int) -> None:
        self._client.send_message(
            QueueUrl=settings.sqs_queue_url,
            MessageBody=json.dumps(
                {
                    "task_type": "sample_run",
                    "sample_run_id": sample_run_id,
                }
            ),
        )

    def enqueue_llm_report(self, report_id: int) -> None:
        self._client.send_message(
            QueueUrl=settings.sqs_queue_url,
            MessageBody=json.dumps(
                {
                    "task_type": "llm_report",
                    "report_id": report_id,
                }
            ),
        )
