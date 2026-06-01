# AWS Architecture

HUFSOLVE의 AWS 배포 목표는 제출 요청 폭증 상황에서 API 요청 접수와 채점 작업을 분리하고, 각 계층을 독립적으로 확장하는 것입니다.

## Target Architecture

```text
User Browser
  -> React Frontend
  -> Application Load Balancer
  -> FastAPI API Server Auto Scaling Group
  -> Amazon SQS
  -> Worker Auto Scaling Group
  -> Docker Sandbox
  -> RDS MySQL / S3
  -> CloudWatch
```

## Network Layout

```text
VPC
├── Public Subnet
│   └── Application Load Balancer
├── Private Subnet
│   ├── API Server Auto Scaling Group
│   ├── Worker Auto Scaling Group
│   └── RDS MySQL
└── AWS Managed Services
    ├── Amazon SQS
    ├── Amazon S3
    ├── Amazon ECR
    └── Amazon CloudWatch
```

Private Subnet의 EC2가 SQS, S3, ECR, CloudWatch에 접근하려면 NAT Gateway 또는 VPC Endpoint 구성이 필요합니다.

비용을 낮춘 수업용 기능 검증에서는 기존 public subnet을 API/Worker/RDS subnet 입력으로 재사용하고 EC2에 public IP를 할당할 수 있습니다. 이 경우에도 API는 ALB SG, Worker는 inbound 없음, RDS는 API/Worker SG만 허용합니다. 다만 이 방식은 목표 private subnet 격리를 대체하지 않습니다.

## Security Groups

- ALB: `80/443` from Internet
- API Server: ALB Security Group에서 오는 traffic만 허용
- Worker: 기본 inbound 없음
- RDS: API Server SG와 Worker SG에서 오는 `3306`만 허용

EC2 key pair는 선택 사항이며, 기본 운영 접근은 SSM Session Manager를 사용합니다. SSH가 필요할 때만 key pair와 제한된 source CIDR을 설정합니다.

## IAM Roles

- API EC2 Role
  - SQS `SendMessage`
  - CloudWatch Logs
  - 필요 시 S3 `PutObject`
- Worker EC2 Role
  - SQS `ReceiveMessage`, `DeleteMessage`, `ChangeMessageVisibility`
  - S3 `GetObject`, `PutObject`
  - ECR image pull
  - CloudWatch Logs

## Auto Scaling Metrics

- API Server ASG
  - ALB `RequestCountPerTarget`
  - 또는 EC2 `CPUUtilization`
- Worker ASG
  - SQS `ApproximateNumberOfMessagesVisible`
  - 또는 SQS `ApproximateAgeOfOldestMessage`

## Required AWS Resources

- Application Load Balancer
- API Server Launch Template
- API Server Auto Scaling Group
- SQS Standard Queue
- SQS Dead Letter Queue
- Worker Launch Template
- Worker Auto Scaling Group
- RDS MySQL
- S3 bucket
- ECR repository
- CloudWatch Dashboard/Alarm

## Queue Message Contracts

실제 source code와 testcase는 SQS에 넣지 않습니다. DB가 source of truth입니다.

```json
{ "submission_id": 101 }
```

공개 예제 실행도 같은 Worker sandbox를 사용하지만 제출 기록과 분리합니다.

```json
{ "task_type": "sample_run", "sample_run_id": 201 }
```

## Repository Deployment Artifacts

현재 repository에는 AWS 최소 배포를 위한 CloudFormation starter template이 포함되어 있습니다.

- `infra/aws/cloudformation/hufsolve-core.yaml`
- `infra/aws/parameters.example.json`
- `scripts/aws/bootstrap-api.sh`
- `scripts/aws/bootstrap-worker.sh`
- `scripts/aws/publish-runner-image.sh`

이 템플릿은 API 서버와 Worker를 EC2 Auto Scaling Group으로 배치하고, API는 ALB 뒤에 두며, Worker는 SQS queue length alarm을 기준으로 scale out/in합니다. 자세한 배포 명령은 `infra/aws/README.md`를 확인합니다.

RDS password는 Secrets Manager에서 생성하고 API/Worker EC2 role이 부팅 시 조회합니다. Worker bootstrap은 ECR runner 이미지를 우선 pull하고, 최초 배포처럼 repository가 비어 있으면 로컬 빌드로 기동합니다. API/Worker 로그는 CloudWatch Agent를 통해 각각의 log group으로 전송하며, S3 artifact bucket은 향후 source code와 대용량 testcase 저장 경로로 사용할 수 있습니다. CloudWatch dashboard에서는 SQS backlog와 Worker ASG capacity를 함께 확인합니다.
