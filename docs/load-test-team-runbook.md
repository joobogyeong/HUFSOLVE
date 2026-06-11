# 동시 대량 제출 부하 테스트 실행 안내

이 테스트는 API/Worker가 각각 1대인 상태에서 다수 사용자가 동시에 코드를 제출하고,
API ASG, SQS, Worker ASG가 부하에 따라 확장되는지 검증합니다.

Locust 기본 제출 코드는 제한 시간까지 CPU를 점유하는 무한 루프입니다. 따라서
`TIME_LIMIT_EXCEEDED`는 예상된 최종 상태이며, Worker queue와 CPU에 최악 부하를 만들기
위한 테스트 입력입니다.

## 현재 테스트 구성

- 대상 ALB: `http://hufsol-Appli-49KjkOXL4Z15-1479776458.ap-northeast-2.elb.amazonaws.com`
- API ASG: 최소/초기 1대, 최대 3대, 평균 CPU 55% 기준 확장
- Worker ASG: 최소/초기 1대, 최대 5대, SQS backlog 기준 확장
- CloudWatch dashboard: `hufsolve-operations`

Locust는 ALB를 직접 호출해야 합니다. 테스트 중 `/wake` endpoint를 호출하면 이미 확장된
ASG desired capacity가 다시 1로 설정될 수 있으므로 호출하지 않습니다.

이 설정은 ASG에 적용한 임시 테스트 설정입니다. 테스트 중 CloudFormation stack update를
실행하면 원래 parameter 값인 0대로 돌아갈 수 있으므로 stack update를 실행하지 않습니다.

## 테스트 전 준비

저장소 루트의 PowerShell에서 실행합니다.

```powershell
.\scripts\aws\configure-load-test.ps1 -Mode prepare
pip install -r scripts/requirements.txt
New-Item -ItemType Directory -Force load-test-results | Out-Null
```

API와 Worker가 모두 `InService=1`이 된 것을 확인한 후 테스트를 시작합니다.

## 권장 실행 단계

먼저 50명으로 연결과 요청 형식을 확인합니다.

```powershell
locust -f scripts/locustfile.py `
  --host http://hufsol-Appli-49KjkOXL4Z15-1479776458.ap-northeast-2.elb.amazonaws.com `
  --headless --users 50 --spawn-rate 50 --run-time 10m `
  --csv load-test-results/burst-50
```

정상 동작하면 200명을 약 1초 안에 투입합니다.

```powershell
locust -f scripts/locustfile.py `
  --host http://hufsol-Appli-49KjkOXL4Z15-1479776458.ap-northeast-2.elb.amazonaws.com `
  --headless --users 200 --spawn-rate 200 --run-time 15m `
  --csv load-test-results/burst-200 `
  --html load-test-results/burst-200.html
```

더 강한 burst가 필요하면 `--users`와 `--spawn-rate`를 동일하게 500까지 단계적으로
높입니다. 한 번에 지나치게 높이지 말고 각 단계에서 오류율과 RDS/API 상태를 확인합니다.

## 확인할 지표

- Locust `POST /submissions` 실패율과 응답 시간
- Locust `GET /submissions/:submissionId` 실패율과 응답 시간
- ALB request count와 target response time
- API ASG desired/in-service capacity
- API EC2 평균 CPU
- SQS visible/in-flight message 수와 oldest message age
- Worker ASG desired/in-service capacity
- 제출 최종 상태와 전체 처리 완료 시간

## 테스트 종료 후 원복

결과 수집이 끝난 뒤 실행합니다.

```powershell
.\scripts\aws\configure-load-test.ps1 -Mode restore
```

원복하면 API/Worker ASG가 다시 최소 0대, desired 0대인 scale-to-zero 상태로 돌아갑니다.
