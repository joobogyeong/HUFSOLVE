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
        self._client.send_message(
            QueueUrl=settings.sqs_queue_url,
            MessageBody=json.dumps({"submission_id": submission_id}),
        )

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
