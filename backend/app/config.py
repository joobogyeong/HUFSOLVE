from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default

    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default

    return int(value)


def _get_list(name: str, default: list[str]) -> list[str]:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default

    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    app_env: str = os.getenv("APP_ENV", "local")
    app_name: str = os.getenv("APP_NAME", "HUFSOLVE")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    backend_host: str = os.getenv("BACKEND_HOST", "0.0.0.0")
    backend_port: int = _get_int("BACKEND_PORT", 8000)
    backend_cors_origins: list[str] = None  # type: ignore[assignment]

    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./hufsolve.db")
    auto_create_tables: bool = _get_bool("AUTO_CREATE_TABLES", True)
    auto_seed: bool = _get_bool("AUTO_SEED", True)

    queue_backend: str = os.getenv("QUEUE_BACKEND", "local").lower()
    aws_region: str = os.getenv("AWS_REGION", "ap-northeast-2")
    sqs_queue_url: str = os.getenv("SQS_QUEUE_URL", "")

    worker_poll_wait_seconds: int = _get_int("WORKER_POLL_WAIT_SECONDS", 10)
    worker_visibility_timeout_seconds: int = _get_int(
        "WORKER_VISIBILITY_TIMEOUT_SECONDS",
        60,
    )
    worker_max_receive_count: int = _get_int("WORKER_MAX_RECEIVE_COUNT", 3)

    judge_docker_image: str = os.getenv("JUDGE_DOCKER_IMAGE", "judge-python:3.11")
    judge_base_tmp_dir: str = os.getenv("JUDGE_BASE_TMP_DIR", "/tmp/hufsolve")
    judge_default_time_limit_ms: int = _get_int("JUDGE_DEFAULT_TIME_LIMIT_MS", 2000)
    judge_default_memory_limit_mb: int = _get_int("JUDGE_DEFAULT_MEMORY_LIMIT_MB", 128)
    judge_cpu_limit: str = os.getenv("JUDGE_CPU_LIMIT", "0.5")
    judge_pids_limit: int = _get_int("JUDGE_PIDS_LIMIT", 64)
    judge_max_output_bytes: int = _get_int("JUDGE_MAX_OUTPUT_BYTES", 65536)
    judge_container_startup_grace_seconds: int = _get_int(
        "JUDGE_CONTAINER_STARTUP_GRACE_SECONDS",
        5,
    )

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "backend_cors_origins",
            _get_list("BACKEND_CORS_ORIGINS", ["http://localhost:5173"]),
        )


settings = Settings()
