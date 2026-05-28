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

## Security Groups

- ALB: `80/443` from Internet
- API Server: ALB Security Group에서 오는 traffic만 허용
- Worker: 기본 inbound 없음
- RDS: API Server SG와 Worker SG에서 오는 `3306`만 허용

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
