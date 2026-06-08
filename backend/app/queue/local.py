from __future__ import annotations


class LocalQueueClient:
    def enqueue_submissions(self, submission_ids: list[int]) -> list[int]:
        # Local workers claim PENDING submissions directly from the database.
        return []

    def enqueue_submission(self, submission_id: int) -> None:
        # Local workers claim PENDING submissions directly from the database.
        return None

    def enqueue_sample_run(self, sample_run_id: int) -> None:
        # Local workers claim PENDING sample runs directly from the database.
        return None

    def enqueue_llm_report(self, report_id: int) -> None:
        # Local workers claim PENDING LLM reports directly from the database.
        return None
