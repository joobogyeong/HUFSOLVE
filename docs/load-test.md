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

## Script Plan

`scripts/` 디렉토리에 부하 테스트 스크립트를 추가할 예정입니다.

예상 입력:

- API base URL
- problem id
- concurrent users
- total submissions
- request timeout

예상 출력:

- 요청 성공/실패 수
- 평균 PENDING 응답 시간
- 최종 채점 완료 평균 시간
- 상태별 제출 수
