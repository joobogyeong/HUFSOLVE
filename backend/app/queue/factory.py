from __future__ import annotations

from .base import QueueClient
from .local import LocalQueueClient
from .sqs import SqsQueueClient
from ..config import settings


def get_queue_client() -> QueueClient:
    if settings.queue_backend == "sqs":
        return SqsQueueClient()

    return LocalQueueClient()
