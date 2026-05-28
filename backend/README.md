# Backend

FastAPI API 서버가 들어갈 디렉토리입니다.

역할:

- 문제 목록/상세 조회
- 제출 접수
- RDS에 submission 저장
- SQS에 `submission_id` 메시지 전송
- 제출 상태 조회

API 서버는 사용자 코드를 직접 실행하지 않습니다.
