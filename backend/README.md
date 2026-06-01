# Backend

FastAPI API 서버입니다. API 서버는 사용자 코드를 직접 실행하지 않고, 제출을 DB에 `PENDING` 상태로 저장한 뒤 queue backend에 `submission_id`만 전달합니다.

## Local Run

repo root에서 실행합니다.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

기본값은 `DATABASE_URL=sqlite:///./hufsolve.db`, `QUEUE_BACKEND=local`입니다. 별도 DB 없이 로컬 파일 DB를 만들고 seed 시험/문제 데이터를 넣습니다.

PowerShell에서 환경변수를 지정하려면:

```powershell
$env:DATABASE_URL="sqlite:///./hufsolve.db"
$env:QUEUE_BACKEND="local"
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

## API

- `GET /health`
- `GET /exams`
- `GET /exams/{room_code}`
- `GET /problems/{problem_id}`
- `POST /submissions`
- `GET /submissions/{submission_id}`
- `POST /runs`
- `GET /runs/{run_id}`
- `POST /exam-attempts`
- `GET /exam-attempts?studentId={student_id}`

## Queue Backends

- `QUEUE_BACKEND=local`: Worker가 DB의 `PENDING` 제출을 직접 claim합니다.
- `QUEUE_BACKEND=sqs`: API 서버가 Amazon SQS에 최소 참조 ID만 보냅니다. 채점은 `{ "submission_id": number }`, 공개 예제 실행은 `{ "task_type": "sample_run", "sample_run_id": number }`를 사용합니다. 이때 `SQS_QUEUE_URL`이 필요합니다.

## Production Notes

AWS 배포에서는 `DATABASE_URL`을 RDS MySQL 접속 문자열로 바꾸고, `QUEUE_BACKEND=sqs`와 `SQS_QUEUE_URL`을 설정합니다. API 서버에는 SQS `SendMessage` 권한이 있는 IAM Role이 필요합니다.
