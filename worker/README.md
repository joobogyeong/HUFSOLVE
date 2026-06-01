# Worker

SQS 또는 local DB queue에서 채점 작업을 가져와 Docker Sandbox로 사용자 코드를 실행하는 Worker입니다.

역할:

- queue에서 `submission_id` 또는 `sample_run_id` 수신
- DB에서 제출 코드와 테스트케이스 조회
- Docker 컨테이너에서 Python 코드 실행
- 결과를 DB에 저장

Worker는 stateless하게 유지해 Auto Scaling Group에서 여러 대로 확장 가능해야 합니다.

## Local Run

먼저 Python runner 이미지를 repo root에서 빌드합니다.

```bash
docker build -t judge-python:3.11 docker/python-runner
```

의존성을 설치합니다.

```bash
pip install -r worker/requirements.txt
```

Worker를 한 번만 실행해 pending 제출 하나를 처리합니다.

```bash
python -m worker.main --once
```

계속 실행하려면:

```bash
python -m worker.main
```

## Queue Modes

- `QUEUE_BACKEND=local`: DB에서 `PENDING` 제출을 직접 가져옵니다. 로컬 통합 테스트용입니다.
- `QUEUE_BACKEND=sqs`: SQS long polling으로 메시지를 가져옵니다. Worker EC2에는 `ReceiveMessage`, `DeleteMessage`, `ChangeMessageVisibility` 권한이 필요합니다.

## Retry and DLQ

- local queue mode에서 system exception이 발생하면 제출 상태를 바로 `SYSTEM_ERROR`로 저장합니다.
- SQS mode에서는 system exception이 발생해도 메시지를 삭제하지 않습니다.
- SQS `ApproximateReceiveCount`가 `WORKER_MAX_RECEIVE_COUNT`에 도달하면 제출 상태를 `SYSTEM_ERROR`로 저장하고, queue redrive policy가 메시지를 DLQ로 이동시킵니다.
- 사용자 코드의 오답, 시간초과, 메모리초과, 런타임 에러는 정상 채점 결과이므로 DB에 결과를 저장하고 메시지를 삭제합니다.

공개 예제 실행은 `sample_runs` 테이블에 별도로 저장합니다. 제출 기록과 섞지 않으며, API 서버가 직접 사용자 코드를 실행하지 않는 원칙은 동일합니다.

## Docker Sandbox

Worker는 제출 코드를 임시 디렉토리의 `main.py`로 저장하고 다음 제한을 걸어 컨테이너에서 실행합니다.

- `--network none`
- `--read-only`
- `--cap-drop ALL`
- `--security-opt no-new-privileges=true`
- `--tmpfs /tmp:rw,noexec,nosuid,size=16m`
- `--memory {problem.memory_limit_mb}m`
- `--cpus {JUDGE_CPU_LIMIT}`
- `--pids-limit {JUDGE_PIDS_LIMIT}`
- `--rm`

시간 제한은 Worker의 host-side 실행 supervisor가 적용합니다.
Worker가 캡처하는 stdout/stderr 합계는 `JUDGE_MAX_OUTPUT_BYTES`로 제한합니다. 상한을 넘으면 컨테이너를 종료하고 `OUTPUT_LIMIT_EXCEEDED`로 기록합니다.

사용자 코드의 시간 제한은 컨테이너 내부 GNU `timeout`으로 적용합니다. host supervisor는 Docker 기동 지연을 허용하기 위해 `JUDGE_CONTAINER_STARTUP_GRACE_SECONDS`만큼 추가로 기다린 뒤, 응답이 없으면 컨테이너를 강제 종료합니다.
