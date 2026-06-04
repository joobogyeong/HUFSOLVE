# HUFSOLVE

클라우드 컴퓨팅 과목 프로젝트: **AWS 기반 코드 자동 채점 서비스**

HUFSOLVE는 시험 종료 직후 제출 요청이 순간적으로 몰리는 상황을 가정하고, AWS의 Load Balancer, Auto Scaling, SQS를 활용해 요청 접수와 채점 작업을 분리 처리하는 프로젝트입니다.

## 핵심 목표

- 사용자는 React 화면에서 문제를 조회하고 Python 코드를 제출합니다.
- FastAPI API 서버는 제출을 빠르게 접수하고 RDS에 저장한 뒤, SQS에 `submission_id`만 전달합니다.
- 공개 예제 실행도 API 서버에서 직접 수행하지 않고, 별도 `sample_run_id`를 Worker에 전달합니다.
- Worker는 SQS에서 작업을 가져와 Docker Sandbox 안에서 사용자 코드를 실행합니다.
- 채점 결과는 RDS에 저장되고, Frontend는 polling으로 결과를 확인합니다.
- AWS 배포 시 ALB, API Server Auto Scaling Group, Worker Auto Scaling Group, SQS, CloudWatch를 통해 제출 폭증 상황을 검증합니다.

## 목표 아키텍처

```text
User Browser
  -> React Frontend
  -> API Gateway HTTP API / Lambda wake endpoint
  -> Application Load Balancer
  -> FastAPI API Server Auto Scaling Group
  -> Amazon SQS
  -> Worker Auto Scaling Group
  -> Docker Sandbox
  -> RDS MySQL / S3
  -> CloudWatch
```

## Repository Structure

```text
HUFSOLVE/
├── frontend/              # React + Vite frontend
├── backend/               # FastAPI API server
├── worker/                # SQS polling and judging worker
├── docker/
│   └── python-runner/     # Python judge Docker image
├── docs/                  # Architecture, deployment, load-test docs
├── infra/                 # AWS CloudFormation deployment artifacts
├── scripts/               # Seed/load-test/helper scripts
├── tests/                 # Backend/worker integration tests
├── .github/               # Issue/PR templates and collaboration flow
├── .env.example           # Shared environment variable template
└── README.md
```

## MVP Scope

### Frontend

- 문제 목록 페이지
- 문제 풀이 페이지
- 제출 결과 조회 화면
- 제출 후 `GET /submissions/{submission_id}` polling
- 공개 예제 실행 후 `GET /runs/{run_id}` polling

### Backend

- FastAPI + SQLAlchemy
- RDS MySQL 연동
- Amazon SQS에 채점 작업 등록
- API 서버는 사용자 코드를 직접 실행하지 않음

### Worker

- SQS long polling
- RDS에서 제출 코드와 테스트케이스 조회
- Docker 컨테이너에서 Python 코드 실행
- 정답/오답/시간초과/런타임 에러 결과 저장

### AWS

- ALB
- API Server Auto Scaling Group
- Worker Auto Scaling Group
- Amazon SQS + DLQ
- RDS MySQL
- S3
- ECR
- CloudWatch
- API Gateway HTTP API / Lambda wake endpoint
- CloudWatch/EventBridge idle cost guard

## Local Development Plan

구현은 다음 순서로 진행합니다.

1. 기본 repository 구조와 협업 문서 구성
2. Frontend 화면 구현
3. Backend API 구현
4. Worker와 Docker Sandbox 구현
5. 로컬 통합 테스트
6. AWS 배포 가이드 작성
7. 부하 테스트와 Auto Scaling 검증

## Environment Variables

민감한 값은 repository에 커밋하지 않습니다. 로컬에서는 `.env`를 만들고, 필요한 키 목록은 `.env.example`을 기준으로 맞춥니다.

```text
cp .env.example .env
```

`.env`에는 DB 접속 정보, AWS region, SQS URL, S3 bucket, ECR image URI 등을 저장합니다.

## GitHub Flow

이 저장소는 작은 기능 단위 branch와 pull request 중심으로 작업합니다.

```text
main
  <- feature/frontend-initial-layout
  <- feature/backend-submission-api
  <- feature/worker-sqs-judge
  <- docs/aws-architecture
```

자세한 작업 흐름은 [.github/DEVELOPMENT_FLOW.md](.github/DEVELOPMENT_FLOW.md)를 확인합니다.

## Documents

- [AWS Architecture](docs/aws-architecture.md)
- [AWS Deployment](infra/aws/README.md)
- [Local Backend/Worker Integration](docs/local-integration.md)
- [Load Test Plan](docs/load-test.md)
- [Scripts](scripts/README.md)

## Verification

```bash
python -m unittest discover -s tests -v
python -m compileall backend worker scripts tests
python scripts/local_docker_e2e.py
cd frontend
npm run build
```

## Important Notes

- API 서버는 사용자 코드를 직접 실행하지 않습니다.
- 채점 SQS 메시지는 `{ "submission_id": number }` 형태만 사용합니다.
- 공개 예제 실행은 `{ "task_type": "sample_run", "sample_run_id": number }` 형태의 최소 참조 메시지를 사용합니다.
- Python 인터프리터는 API 서버가 아니라 Docker runner image 안에 둡니다.
- Cognito, SES, DynamoDB, Kubernetes, ECS, LLM 피드백, 다중 언어 채점은 MVP 범위에서 제외합니다.
- 실제 AWS 리소스 생성은 AWS Console 또는 IaC 도구로 별도 진행합니다. 이 repository는 애플리케이션 코드, Worker 코드, Docker 이미지 정의, 배포 문서, 부하 테스트 도구를 제공합니다.
