from __future__ import annotations

import json
from dataclasses import dataclass

from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.database import SessionLocal
from backend.app.models import LlmReport, SampleRun, Submission
from worker.judge import mark_sample_run_system_error, mark_submission_system_error
from worker.review import mark_llm_report_system_error


@dataclass(frozen=True)
class WorkerMessage:
    task_type: str
    resource_id: int
    receipt_handle: str | None = None
    receive_count: int = 1


class LocalWorkerQueue:
    def receive(self) -> WorkerMessage | None:
        db = SessionLocal()
        try:
            llm_report = _claim_next_pending_llm_report(db)
            if llm_report is not None:
                return WorkerMessage(task_type="llm_report", resource_id=llm_report.id)

            sample_run = _claim_next_pending_sample_run(db)
            if sample_run is not None:
                return WorkerMessage(task_type="sample_run", resource_id=sample_run.id)

            submission = _claim_next_pending_submission(db)
            if submission is None:
                return None

            return WorkerMessage(task_type="submission", resource_id=submission.id)
        finally:
            db.close()

    def ack(self, message: WorkerMessage) -> None:
        return None

    def fail(self, message: WorkerMessage, exc: Exception) -> None:
        _mark_system_error(message, exc)


class SqsWorkerQueue:
    def __init__(self) -> None:
        if not settings.sqs_queue_url:
            raise RuntimeError("SQS_QUEUE_URL is required when QUEUE_BACKEND=sqs")

        import boto3

        self._client = boto3.client("sqs", region_name=settings.aws_region)

    def receive(self) -> WorkerMessage | None:
        response = self._client.receive_message(
            QueueUrl=settings.sqs_queue_url,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=settings.worker_poll_wait_seconds,
            VisibilityTimeout=settings.worker_visibility_timeout_seconds,
            MessageSystemAttributeNames=["ApproximateReceiveCount"],
        )
        messages = response.get("Messages", [])
        if not messages:
            return None

        message = messages[0]
        body = json.loads(message["Body"])
        task_type = str(body.get("task_type", "submission"))
        if task_type == "sample_run":
            resource_id = int(body["sample_run_id"])
        elif task_type == "llm_report":
            resource_id = int(body["report_id"])
        else:
            resource_id = int(body["submission_id"])
        return WorkerMessage(
            task_type=task_type,
            resource_id=resource_id,
            receipt_handle=message["ReceiptHandle"],
            receive_count=int(message.get("Attributes", {}).get("ApproximateReceiveCount", "1")),
        )

    def ack(self, message: WorkerMessage) -> None:
        if message.receipt_handle is None:
            return

        self._client.delete_message(
            QueueUrl=settings.sqs_queue_url,
            ReceiptHandle=message.receipt_handle,
        )

    def fail(self, message: WorkerMessage, exc: Exception) -> None:
        if message.receive_count >= settings.worker_max_receive_count:
            _mark_system_error(message, exc)


def build_worker_queue() -> LocalWorkerQueue | SqsWorkerQueue:
    if settings.queue_backend == "sqs":
        return SqsWorkerQueue()

    return LocalWorkerQueue()


def _claim_next_pending_submission(db: Session) -> Submission | None:
    while True:
        submission_id = (
            db.query(Submission.id)
            .filter(Submission.status == "PENDING")
            .order_by(Submission.created_at.asc(), Submission.id.asc())
            .limit(1)
            .scalar()
        )

        if submission_id is None:
            return None

        claimed_count = (
            db.query(Submission)
            .filter(
                Submission.id == submission_id,
                Submission.status == "PENDING",
            )
            .update({"status": "RUNNING"}, synchronize_session=False)
        )
        db.commit()

        if claimed_count == 1:
            return db.get(Submission, submission_id)


def _claim_next_pending_llm_report(db: Session) -> LlmReport | None:
    while True:
        report_id = (
            db.query(LlmReport.id)
            .filter(LlmReport.status == "PENDING")
            .order_by(LlmReport.created_at.asc(), LlmReport.id.asc())
            .limit(1)
            .scalar()
        )

        if report_id is None:
            return None

        claimed_count = (
            db.query(LlmReport)
            .filter(
                LlmReport.id == report_id,
                LlmReport.status == "PENDING",
            )
            .update({"status": "RUNNING"}, synchronize_session=False)
        )
        db.commit()

        if claimed_count == 1:
            return db.get(LlmReport, report_id)


def _claim_next_pending_sample_run(db: Session) -> SampleRun | None:
    while True:
        sample_run_id = (
            db.query(SampleRun.id)
            .filter(SampleRun.status == "PENDING")
            .order_by(SampleRun.created_at.asc(), SampleRun.id.asc())
            .limit(1)
            .scalar()
        )

        if sample_run_id is None:
            return None

        claimed_count = (
            db.query(SampleRun)
            .filter(
                SampleRun.id == sample_run_id,
                SampleRun.status == "PENDING",
            )
            .update({"status": "RUNNING"}, synchronize_session=False)
        )
        db.commit()

        if claimed_count == 1:
            return db.get(SampleRun, sample_run_id)


def _mark_system_error(message: WorkerMessage, exc: Exception) -> None:
    if message.task_type == "llm_report":
        mark_llm_report_system_error(message.resource_id, str(exc))
        return

    if message.task_type == "sample_run":
        mark_sample_run_system_error(message.resource_id, str(exc))
        return

    mark_submission_system_error(message.resource_id, str(exc))
