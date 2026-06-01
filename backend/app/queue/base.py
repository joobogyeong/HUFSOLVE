from __future__ import annotations

from typing import Protocol


class QueueClient(Protocol):
    def enqueue_submission(self, submission_id: int) -> None:
        pass

    def enqueue_sample_run(self, sample_run_id: int) -> None:
        pass
