# Load Test Plan

이 문서는 시험 종료 직후 제출 요청이 몰리는 상황을 재현하고, AWS Auto Scaling 동작을 검증하기 위한 계획입니다.

## Goal

동시에 다수의 코드 제출 요청을 발생시켜 다음 흐름을 확인합니다.

```text
Burst submissions
  -> API Server returns PENDING quickly
  -> SQS queue length increases
  -> Worker ASG scales out
  -> Workers process jobs in parallel
  -> SQS queue length decreases
  -> Submissions reach final status
```

## Metrics

CloudWatch에서 다음 지표를 확인합니다.

- ALB `RequestCount`
- API EC2 `CPUUtilization`
- SQS `ApproximateNumberOfMessagesVisible`
- SQS `ApproximateAgeOfOldestMessage`
- Worker ASG `DesiredCapacity`
- Worker ASG `InServiceInstances`
- 평균 제출 완료 시간

## Script

부하 테스트 스크립트는 `scripts/load_test.py`입니다.

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

입력:

- API base URL
- problem id
- concurrent users
- total submissions
- request timeout
- polling timeout
- optional source file

출력:

- 요청 성공/실패 수
- API의 `PENDING` 응답 latency
- 최종 채점 완료 latency
- 상태별 제출 수
- timeout/error sample

## Validation Criteria

- API가 burst 상황에서도 빠르게 `PENDING`을 반환한다.
- SQS `ApproximateNumberOfMessagesVisible`가 증가한 뒤 Worker 처리에 따라 감소한다.
- Worker Auto Scaling Group desired capacity가 queue alarm에 따라 증가한다.
- 대부분의 제출이 `--poll-timeout` 안에 terminal status에 도달한다.
