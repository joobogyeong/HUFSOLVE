# Scripts

개발과 검증을 돕는 스크립트가 들어갈 디렉토리입니다.

## Load Test

`load_test.py`는 API에 제출 요청을 한꺼번에 보내고, 각 제출이 최종 채점 상태가 될 때까지 polling한 뒤 JSON 요약을 출력합니다.

의존성 설치:

```bash
pip install -r scripts/requirements.txt
```

로컬 예시:

```bash
python scripts/load_test.py \
  --api-base-url http://127.0.0.1:8000 \
  --problem-id 1 \
  --total 20 \
  --concurrency 5
```

AWS 예시:

```bash
python scripts/load_test.py \
  --api-base-url http://<alb-dns> \
  --problem-id 1 \
  --total 200 \
  --concurrency 40 \
  --poll-timeout 300
```

주요 출력:

- `acceptedLatencyMs`: API가 `PENDING`을 반환하기까지 걸린 시간
- `completedLatencyMs`: 제출부터 최종 채점 완료까지 걸린 시간
- `statusCounts`: 최종 채점 상태 분포
- `failedOrTimedOutCount`: 요청 실패 또는 timeout된 제출 수

## Preflight

로컬 Docker 채점을 시작하기 전에:

```bash
python scripts/preflight.py --mode local
```

AWS 배포 전에:

```bash
python scripts/preflight.py --mode aws
```

AWS mode는 Docker daemon, AWS CLI, CloudFormation template, `infra/aws/parameters.local.json` 존재 여부를 확인합니다.

## Local Docker E2E

Python runner 이미지를 빌드한 뒤 FastAPI, local queue, Worker, Docker sandbox, 결과 저장을 한 번에 검증합니다.

```bash
docker build -t judge-python:3.11 docker/python-runner
python scripts/local_docker_e2e.py
```

검증용 SQLite DB와 sandbox 파일은 `tmp/` 아래에 만들고 실행 종료 시 정리합니다.

## AWS Bootstrap

`scripts/aws/bootstrap-api.sh`와 `scripts/aws/bootstrap-worker.sh`는 CloudFormation UserData와 같은 역할을 하는 독립 bootstrap 스크립트입니다. Auto Scaling Group 전에 수동 EC2 한 대씩으로 API/Worker를 검증할 때 사용할 수 있습니다.

Worker bootstrap에서 `ECR_PYTHON_RUNNER_IMAGE=<repository-uri>:3.11`을 설정하면 ECR 이미지를 우선 pull합니다. 이미지가 없거나 pull할 수 없으면 로컬 빌드로 fallback합니다.

스택 생성 후 runner 이미지를 ECR에 게시할 때:

```bash
export ECR_REPOSITORY_URI=<cloudformation-output-uri>
bash scripts/aws/publish-runner-image.sh
```
