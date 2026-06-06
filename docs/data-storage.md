# RDS 및 S3 데이터 저장 설계

HUFSOLVE는 DynamoDB를 사용하지 않습니다. 관계와 조회 조건이 중요한 데이터는 RDS MySQL에 저장하고, 크기가 계속 증가하거나 파일 성격이 강한 데이터는 S3 artifact bucket에 저장합니다.

## RDS

기준 정보와 상태, S3 객체의 참조를 저장합니다.

- 사용자: `users`, `professors`, `students`
- 수업: `courses`, `course_professors`, `course_enrollments`
- 시험: `exams`, `exam_courses`, `exam_attempts`
- 문제 메타데이터: `problems`, `problem_artifacts`
- 채점 메타데이터와 요약: `submissions`, `submission_artifacts`, `sample_runs`, `sample_run_artifacts`

기존 `exams.course`, `exams.professor`와 문제/코드 본문 컬럼은 기존 데이터 호환용 fallback으로 유지합니다. 새 관계형 테이블과 artifact 참조가 있으면 이를 우선 사용합니다.

## S3

S3 객체 key는 RDS의 artifact 테이블에 저장합니다.

```text
problems/{problem-id}/versions/{version}/statement.json
problems/{problem-id}/versions/{version}/testcases.json
submissions/{year}/{month}/{submission-id}/source.py
submissions/{year}/{month}/{submission-id}/result.json
sample-runs/{year}/{month}/{run-id}/source.py
sample-runs/{year}/{month}/{run-id}/result.json
```

- 문제 본문과 테스트케이스는 문제 버전별 객체로 저장합니다.
- 제출 코드와 공개 예제 실행 코드는 API가 저장합니다.
- Worker는 S3에서 코드와 테스트케이스를 읽고 상세 결과 JSON을 S3에 저장합니다.
- RDS에는 상태, 점수, 실행 시간, 오류 요약, S3 key, SHA-256을 저장합니다.
- SQS에는 기존과 동일하게 `submission_id` 또는 `sample_run_id`만 넣습니다.

AWS bucket은 암호화, public access 차단, versioning, TLS 강제 정책을 사용합니다. 임시 성격의 `sample-runs/` 객체는 30일 뒤 만료됩니다.

## Bootstrap

AWS API 인스턴스 bootstrap은 다음 명령을 실행하여 새 관계형 테이블을 만들고 기존 시험 데이터를 정규화한 뒤 문제 artifact를 S3에 생성합니다.

```bash
python -m backend.app.bootstrap --seed-if-empty
```

실데이터가 이미 있고 demo 시험을 만들면 안 되는 환경에서는 `--seed-if-empty` 없이 실행합니다.

```bash
python -m backend.app.bootstrap
```

로컬에서는 `ARTIFACT_BACKEND=local`과 `ARTIFACT_LOCAL_DIR=./tmp/artifacts`를 사용합니다. AWS에서는 `ARTIFACT_BACKEND=s3`와 `S3_BUCKET_NAME`을 사용합니다.

CloudFormation UserData와 `scripts/aws/bootstrap-api.sh`, `scripts/aws/bootstrap-worker.sh`는 동일하게 AWS에서 `ARTIFACT_BACKEND=s3`를 설정합니다. API bootstrap만 schema 생성과 기존 데이터 이전을 수행하고 Worker는 생성된 schema와 artifact를 사용합니다.
