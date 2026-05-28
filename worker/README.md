# Worker

SQS에서 채점 작업을 가져와 Docker Sandbox로 사용자 코드를 실행하는 Worker 코드가 들어갈 디렉토리입니다.

역할:

- SQS long polling
- RDS에서 제출 코드와 테스트케이스 조회
- Docker 컨테이너에서 Python 코드 실행
- 결과를 RDS에 저장

Worker는 stateless하게 유지해 Auto Scaling Group에서 여러 대로 확장 가능해야 합니다.
