from __future__ import annotations

from typing import Protocol


class QueueClient(Protocol):
    def enqueue_submissions(self, submission_ids: list[int]) -> list[int]:
        pass

    def enqueue_submission(self, submission_id: int) -> None:
        pass

    def enqueue_sample_run(self, sample_run_id: int) -> None:
        pass

    def enqueue_llm_report(self, report_id: int) -> None:
        pass
