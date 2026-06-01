# Local Backend/Worker Integration

이 문서는 Notion의 서버 아키텍처, Worker 구현 예시, Python 인터프리터 설계를 현재 repo 구현에 맞춰 실행하는 순서입니다.

## 1. Backend 실행

```bash
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

기본값:

- `DATABASE_URL=sqlite:///./hufsolve.db`
- `QUEUE_BACKEND=local`
- `AUTO_CREATE_TABLES=true`
- `AUTO_SEED=true`
- `JUDGE_MAX_OUTPUT_BYTES=65536`
- `JUDGE_CONTAINER_STARTUP_GRACE_SECONDS=5`

## 2. Frontend 실행

```bash
cd frontend
npm install
npm run dev
```

프론트엔드는 `VITE_API_BASE_URL=http://localhost:8000`을 사용합니다. 백엔드가 꺼져 있으면 기존 mock 판정으로 fallback합니다.

## 3. Python Runner 이미지 빌드

환경 점검:

```bash
python scripts/preflight.py --mode local
```

```bash
docker build -t judge-python:3.11 docker/python-runner
```

Python 인터프리터는 API 서버가 아니라 이 Docker 이미지 안에 포함됩니다.

## 4. Worker 실행

repo root에서 실행합니다.

```bash
pip install -r worker/requirements.txt
python -m worker.main
```

한 제출만 처리하려면:

```bash
python -m worker.main --once
```

## 5. 제출 흐름

```text
React
  -> POST /runs
  -> sample_runs.status = PENDING
  -> Worker가 Docker judge-python:3.11 실행
  -> React polling: GET /runs/{run_id}

React
  -> POST /submissions
  -> submissions.status = PENDING
  -> local queue mode: Worker가 DB에서 PENDING claim
  -> Docker judge-python:3.11 실행
  -> submissions.status = ACCEPTED / WRONG_ANSWER / TIME_LIMIT_EXCEEDED / MEMORY_LIMIT_EXCEEDED / OUTPUT_LIMIT_EXCEEDED / RUNTIME_ERROR
  -> React polling: GET /submissions/{submission_id}

React 최종 제출
  -> POST /exam-attempts
  -> Backend가 해당 학생의 ACCEPTED 제출을 기준으로 점수 계산
  -> GET /exam-attempts?studentId={student_id}
```

## 6. AWS 전환 지점

로컬 통합 흐름이 확인된 뒤 아래 환경변수만 교체합니다.

```text
DATABASE_URL=mysql+pymysql://...
QUEUE_BACKEND=sqs
SQS_QUEUE_URL=https://sqs.ap-northeast-2.amazonaws.com/...
WORKER_MAX_RECEIVE_COUNT=3
```

그 다음 AWS에서 필요한 작업:

- RDS MySQL 생성 및 API/Worker Security Group에서 3306 허용
- SQS Standard Queue + DLQ 생성
- API EC2 Role에 SQS `SendMessage` 권한 부여
- Worker EC2 Role에 SQS receive/delete/change visibility 권한 부여
- Worker EC2에 Docker 설치 및 `judge-python:3.11` 이미지 준비
- CloudWatch Logs와 SQS queue length alarm 구성

## 7. Automated Tests

Docker daemon 없이 API, local queue claim, Worker 결과 업데이트, SQS retry boundary를 검증할 수 있습니다.

```bash
python -m unittest discover -s tests -v
```

실제 Docker sandbox 검증은 Docker Desktop 또는 Worker EC2의 Docker daemon이 실행 중일 때 별도로 진행합니다.

```bash
python scripts/local_docker_e2e.py
```

이 명령은 FastAPI 요청, local queue claim, Worker 처리, 실제 Docker runner 실행, DB 결과 조회를 한 번에 검증합니다.
