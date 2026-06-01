# AWS Deployment

이 디렉토리는 Notion 아키텍처의 6단계 AWS 최소 배포와 7단계 부하 테스트를 진행하기 위한 배포 산출물입니다.

## What This Stack Creates

- Application Load Balancer
- API Server Auto Scaling Group
- Worker Auto Scaling Group
- Amazon SQS Standard Queue
- Dead Letter Queue
- RDS MySQL
- ECR repository for the Python runner image
- EC2 IAM roles and security groups
- Worker queue-length based scale out/in alarms

## Prerequisites

사용자가 먼저 준비해야 하는 값입니다.

- AWS CLI v2 설치 및 로그인
- VPC ID
- public subnet 2개 이상
- private subnet 2개 이상
- EC2 인스턴스가 clone할 수 있는 Git repository URL
- private subnet의 outbound 경로: NAT Gateway 또는 VPC Endpoint

Private subnet에서 `git clone`, `pip install`, Docker image pull/build, SQS 접근이 필요합니다. NAT Gateway가 없으면 VPC Endpoint와 사설 패키지 경로를 따로 구성해야 합니다.

EC2 key pair는 선택 사항입니다. 비워두면 SSH ingress를 만들지 않고 SSM Session Manager를 사용합니다.

## Network Profiles

목표 아키텍처는 `AssignPublicIpToInstances=false`와 private subnet 2개 이상을 사용합니다. Private subnet에는 NAT Gateway 또는 필요한 VPC Endpoint를 구성합니다.

비용을 낮춰 기능만 검증하는 수업용 프로필에서는 기존 public subnet을 `PrivateSubnetIds`에도 재사용하고 `AssignPublicIpToInstances=true`를 설정할 수 있습니다. API/Worker는 public IP를 받지만 inbound는 보안 그룹으로 제한됩니다. 이 프로필은 private subnet 격리 검증을 대체하지 않으므로 시연 후 리소스를 삭제합니다.

## Deploy

`infra/aws/parameters.example.json`을 `infra/aws/parameters.local.json`으로 복사해 실제 VPC, subnet, 선택적 key pair, repository 값을 입력합니다. RDS 비밀번호는 Secrets Manager가 생성합니다. 로컬 파라미터 파일은 환경별 값이므로 commit하지 않습니다.

배포 전 점검:

```bash
python scripts/preflight.py --mode aws
```

```bash
aws cloudformation create-stack \
  --stack-name hufsolve-core \
  --template-body file://infra/aws/cloudformation/hufsolve-core.yaml \
  --parameters file://infra/aws/parameters.local.json \
  --capabilities CAPABILITY_NAMED_IAM
```

스택 생성이 완료되면 Python runner 이미지를 ECR에 게시합니다.

```bash
export ECR_REPOSITORY_URI=$(aws cloudformation describe-stacks \
  --stack-name hufsolve-core \
  --query "Stacks[0].Outputs[?OutputKey=='PythonRunnerRepositoryUri'].OutputValue" \
  --output text)
bash scripts/aws/publish-runner-image.sh
```

최초 Worker는 ECR이 비어 있으면 로컬 빌드로 기동합니다. 이미지 게시 후 생성되는 Worker 인스턴스는 ECR 이미지를 우선 사용합니다. 기존 Worker도 즉시 ECR 이미지로 교체하려면 instance refresh를 시작합니다.

```bash
WORKER_ASG=$(aws cloudformation describe-stacks \
  --stack-name hufsolve-core \
  --query "Stacks[0].Outputs[?OutputKey=='WorkerAutoScalingGroupName'].OutputValue" \
  --output text)
aws autoscaling start-instance-refresh --auto-scaling-group-name "$WORKER_ASG"
```

업데이트:

```bash
aws cloudformation update-stack \
  --stack-name hufsolve-core \
  --template-body file://infra/aws/cloudformation/hufsolve-core.yaml \
  --parameters file://infra/aws/parameters.local.json \
  --capabilities CAPABILITY_NAMED_IAM
```

Windows PowerShell에서도 같은 AWS CLI 명령을 사용할 수 있습니다.

## Verify

```bash
aws cloudformation describe-stacks \
  --stack-name hufsolve-core \
  --query "Stacks[0].Outputs"
```

`ApiBaseUrl` 출력값으로 확인합니다.

```bash
curl http://<alb-dns>/health
curl http://<alb-dns>/exams
```

## Frontend Configuration

배포된 API 주소를 프론트엔드 환경변수로 설정합니다.

```text
VITE_API_BASE_URL=http://<alb-dns>
```

## Operational Notes

- API 서버는 사용자 코드를 실행하지 않습니다.
- SQS 메시지는 `{ "submission_id": number }`만 포함합니다.
- Worker는 Docker 컨테이너 내부의 Python interpreter로 사용자 코드를 실행합니다.
- Worker bootstrap은 게시된 ECR runner 이미지를 우선 pull하고, 최초 배포처럼 이미지가 아직 없으면 로컬 빌드로 기동합니다.
- `QUEUE_BACKEND=sqs`에서 API는 SQS `SendMessage`, Worker는 SQS receive/delete/change visibility 권한을 사용합니다.
- RDS password는 Secrets Manager가 생성하며 EC2 UserData에 직접 기록하지 않습니다.
- API/Worker systemd 로그는 CloudWatch Logs로 전송합니다.
- `${ProjectName}-operations` CloudWatch dashboard에서 SQS backlog와 Worker ASG capacity를 확인할 수 있습니다.
- S3 artifact bucket은 source code, testcase file, 실행 로그 확장을 위해 생성합니다. 현재 MVP 데이터 경로의 source of truth는 RDS입니다.
- AWS bootstrap에서 schema 생성과 seed는 초기 API 인스턴스가 담당합니다. Worker는 `AUTO_CREATE_TABLES=false`, `AUTO_SEED=false`로 실행해 startup race를 피합니다.
- 템플릿의 EC2 UserData는 수업 프로젝트용 bootstrap입니다. 운영 수준에서는 AMI baking과 HTTPS listener를 추가하는 편이 안전합니다.
