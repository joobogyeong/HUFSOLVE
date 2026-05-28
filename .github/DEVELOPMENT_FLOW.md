# Development Flow

HUFSOLVE는 작은 기능 단위 branch와 pull request 중심으로 작업합니다.

## Branch Naming

```text
feature/frontend-initial-layout
feature/backend-problem-api
feature/worker-sqs-judge
docs/aws-architecture
chore/repo-bootstrap
fix/submission-status-polling
```

## Issue Flow

1. 작업 전에 issue를 생성합니다.
2. issue에는 목표, 구현 범위, 완료 기준을 작성합니다.
3. 하나의 issue는 가능한 한 하나의 기능 또는 문서 작업에 대응시킵니다.
4. 작업 branch는 issue 범위에 맞춰 생성합니다.

## Pull Request Flow

1. PR은 `main` branch를 대상으로 생성합니다.
2. PR 본문에는 변경 요약, 검증 방법, 관련 issue를 적습니다.
3. 민감 정보가 포함되지 않았는지 확인합니다.
4. 최소 한 명이 리뷰한 뒤 merge합니다.

## Commit Style

권장 prefix:

```text
feat: 새로운 기능
fix: 버그 수정
docs: 문서 변경
chore: 설정/구조 변경
refactor: 동작 변경 없는 구조 개선
test: 테스트 추가/수정
```

예시:

```text
feat: add submission polling page
docs: describe worker autoscaling policy
chore: bootstrap monorepo structure
```

## Secret Handling

- `.env`는 commit하지 않습니다.
- `.env.example`에는 키 이름과 예시값만 둡니다.
- AWS access key, DB password, private key, PEM 파일은 repository에 저장하지 않습니다.
