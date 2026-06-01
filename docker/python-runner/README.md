# Python Runner Image

사용자 Python 코드를 실행할 Docker image 정의가 들어갈 디렉토리입니다.

예정 이미지:

```text
judge-python:3.11
```

빌드:

```bash
docker build -t judge-python:3.11 docker/python-runner
```

원칙:

- `python:3.11-slim` 기반
- non-root user 실행
- network disabled
- memory/cpu/pid 제한은 Worker의 `docker run` 옵션에서 적용
