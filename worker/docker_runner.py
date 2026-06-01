from __future__ import annotations

import shutil
import subprocess
import threading
import time
import uuid
from pathlib import Path

from backend.app.config import settings


def run_python_code(
    source_code: str,
    input_data: str,
    time_limit_ms: int | None = None,
    memory_limit_mb: int | None = None,
) -> dict[str, object]:
    run_id = str(uuid.uuid4())
    base_dir = Path(settings.judge_base_tmp_dir)
    work_dir = base_dir / run_id
    work_dir.mkdir(parents=True, exist_ok=True)

    source_path = work_dir / "main.py"
    source_path.write_text(source_code, encoding="utf-8")

    timeout_sec = (time_limit_ms or settings.judge_default_time_limit_ms) / 1000
    memory_mb = memory_limit_mb or settings.judge_default_memory_limit_mb
    container_name = f"hufsolve-{run_id}"

    docker_command = [
        "docker",
        "run",
        "-i",
        "--name",
        container_name,
        "--rm",
        "--network",
        "none",
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges=true",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,size=16m",
        "--memory",
        f"{memory_mb}m",
        "--cpus",
        settings.judge_cpu_limit,
        "--pids-limit",
        str(settings.judge_pids_limit),
        "-v",
        f"{work_dir.resolve()}:/sandbox:ro",
        "-w",
        "/sandbox",
        settings.judge_docker_image,
        "timeout",
        "--verbose",
        "--kill-after=1s",
        f"{timeout_sec}s",
        "python3",
        "main.py",
    ]

    start_time = time.monotonic()

    try:
        process = subprocess.Popen(
            docker_command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr, timed_out, output_limit_exceeded = _communicate_limited(
            process=process,
            input_data=input_data.encode("utf-8"),
            timeout_sec=timeout_sec + settings.judge_container_startup_grace_seconds,
            max_output_bytes=settings.judge_max_output_bytes,
            container_name=container_name,
        )
        execution_time_ms = int((time.monotonic() - start_time) * 1000)
        stdout_text = stdout.decode("utf-8", errors="replace")
        stderr_text = stderr.decode("utf-8", errors="replace")

        if output_limit_exceeded:
            return {
                "status": "OUTPUT_LIMIT_EXCEEDED",
                "stdout": stdout_text,
                "stderr": "Output limit exceeded",
                "execution_time_ms": execution_time_ms,
            }

        if timed_out:
            return {
                "status": "TIME_LIMIT_EXCEEDED",
                "stdout": stdout_text,
                "stderr": "Container startup or execution watchdog exceeded",
                "execution_time_ms": execution_time_ms,
            }

        if process.returncode in {124, 137} and "timeout:" in stderr_text.lower():
            return {
                "status": "TIME_LIMIT_EXCEEDED",
                "stdout": stdout_text,
                "stderr": "Time limit exceeded",
                "execution_time_ms": execution_time_ms,
            }

        if process.returncode == 137:
            return {
                "status": "MEMORY_LIMIT_EXCEEDED",
                "stdout": stdout_text,
                "stderr": stderr_text,
                "execution_time_ms": execution_time_ms,
            }

        if process.returncode != 0:
            return {
                "status": "RUNTIME_ERROR",
                "stdout": stdout_text,
                "stderr": stderr_text,
                "execution_time_ms": execution_time_ms,
            }

        return {
            "status": "OK",
            "stdout": stdout_text,
            "stderr": stderr_text,
            "execution_time_ms": execution_time_ms,
        }

    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


def _communicate_limited(
    process: subprocess.Popen[bytes],
    input_data: bytes,
    timeout_sec: float,
    max_output_bytes: int,
    container_name: str,
) -> tuple[bytes, bytes, bool, bool]:
    stdout_chunks: list[bytes] = []
    stderr_chunks: list[bytes] = []
    state = {"captured": 0}
    lock = threading.Lock()
    limit_exceeded = threading.Event()

    stdout_thread = threading.Thread(
        target=_read_limited,
        args=(process.stdout, stdout_chunks, state, lock, limit_exceeded, max_output_bytes),
        daemon=True,
    )
    stderr_thread = threading.Thread(
        target=_read_limited,
        args=(process.stderr, stderr_chunks, state, lock, limit_exceeded, max_output_bytes),
        daemon=True,
    )
    stdout_thread.start()
    stderr_thread.start()

    if process.stdin is not None:
        try:
            process.stdin.write(input_data)
        except BrokenPipeError:
            pass
        finally:
            process.stdin.close()

    deadline = time.monotonic() + timeout_sec
    timed_out = False

    while process.poll() is None:
        if limit_exceeded.is_set():
            _terminate_execution(process, container_name)
            break

        if time.monotonic() >= deadline:
            timed_out = True
            _terminate_execution(process, container_name)
            break

        time.sleep(0.01)

    stdout_thread.join(timeout=1)
    stderr_thread.join(timeout=1)
    _close_pipe(process.stdout)
    _close_pipe(process.stderr)
    return (
        b"".join(stdout_chunks),
        b"".join(stderr_chunks),
        timed_out,
        limit_exceeded.is_set(),
    )


def _read_limited(
    stream: object,
    chunks: list[bytes],
    state: dict[str, int],
    lock: threading.Lock,
    limit_exceeded: threading.Event,
    max_output_bytes: int,
) -> None:
    if stream is None:
        return

    while not limit_exceeded.is_set():
        chunk = stream.read(4096)
        if not chunk:
            return

        with lock:
            remaining = max(max_output_bytes - state["captured"], 0)
            chunks.append(chunk[:remaining])
            state["captured"] += len(chunk)
            if state["captured"] > max_output_bytes:
                limit_exceeded.set()


def _terminate_execution(process: subprocess.Popen[bytes], container_name: str) -> None:
    try:
        subprocess.run(
            ["docker", "rm", "-f", container_name],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
    except subprocess.TimeoutExpired:
        pass
    if process.poll() is None:
        process.kill()
    try:
        process.wait(timeout=1)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=1)


def _close_pipe(pipe: object) -> None:
    if pipe is not None:
        pipe.close()
