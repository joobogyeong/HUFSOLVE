#!/usr/bin/env bash
set -euo pipefail

: "${REPOSITORY_URL:?REPOSITORY_URL is required}"
: "${REPOSITORY_BRANCH:=main}"
: "${DATABASE_URL:=}"
: "${DATABASE_SECRET_ARN:=}"
: "${DATABASE_HOST:=}"
: "${DATABASE_NAME:=hufsolve}"
: "${SQS_QUEUE_URL:?SQS_QUEUE_URL is required}"
: "${S3_BUCKET_NAME:?S3_BUCKET_NAME is required}"
: "${AWS_REGION:=ap-northeast-2}"
: "${LLM_REVIEW_ENABLED:=false}"
: "${BEDROCK_REVIEW_REGION:=ap-northeast-2}"
: "${BEDROCK_REVIEW_MODEL_ID:=global.amazon.nova-2-lite-v1:0}"
: "${JUDGE_DOCKER_IMAGE:=judge-python:3.11}"
: "${ECR_PYTHON_RUNNER_IMAGE:=}"
: "${JUDGE_MAX_OUTPUT_BYTES:=65536}"
: "${JUDGE_CONTAINER_STARTUP_GRACE_SECONDS:=5}"
: "${CLOUDWATCH_LOG_GROUP:=}"

dnf update -y
dnf install -y amazon-cloudwatch-agent docker git python3.11 python3.11-pip
systemctl enable --now docker
usermod -aG docker ec2-user

mkdir -p /opt/hufsolve
git clone --branch "${REPOSITORY_BRANCH}" "${REPOSITORY_URL}" /opt/hufsolve/app
cd /opt/hufsolve/app

python3.11 -m pip install --upgrade pip
python3.11 -m pip install -r worker/requirements.txt

if [[ -n "${ECR_PYTHON_RUNNER_IMAGE}" ]] \
  && command -v aws >/dev/null \
  && aws ecr get-login-password --region "${AWS_REGION}" |
    docker login --username AWS --password-stdin "${ECR_PYTHON_RUNNER_IMAGE%%/*}" \
  && docker pull "${ECR_PYTHON_RUNNER_IMAGE}"; then
  JUDGE_DOCKER_IMAGE="${ECR_PYTHON_RUNNER_IMAGE}"
  docker logout "${ECR_PYTHON_RUNNER_IMAGE%%/*}"
else
  docker logout "${ECR_PYTHON_RUNNER_IMAGE%%/*}" >/dev/null 2>&1 || true
  docker build -t "${JUDGE_DOCKER_IMAGE}" docker/python-runner
fi

if [[ -z "${DATABASE_URL}" ]]; then
  : "${DATABASE_SECRET_ARN:?DATABASE_SECRET_ARN is required when DATABASE_URL is empty}"
  : "${DATABASE_HOST:?DATABASE_HOST is required when DATABASE_URL is empty}"
  export AWS_REGION DATABASE_SECRET_ARN DATABASE_HOST DATABASE_NAME
  DATABASE_URL=$(python3.11 - <<'PY'
import json
import os
from urllib.parse import quote_plus

import boto3

secret = boto3.client("secretsmanager", region_name=os.environ["AWS_REGION"]).get_secret_value(
    SecretId=os.environ["DATABASE_SECRET_ARN"]
)
data = json.loads(secret["SecretString"])
username = quote_plus(data["username"])
password = quote_plus(data["password"])
database = quote_plus(os.environ["DATABASE_NAME"])
print(f"mysql+pymysql://{username}:{password}@{os.environ['DATABASE_HOST']}:3306/{database}")
PY
  )
fi

install -m 600 /dev/null /opt/hufsolve/app/.env
cat >/opt/hufsolve/app/.env <<ENV
APP_ENV=aws
DATABASE_URL=${DATABASE_URL}
QUEUE_BACKEND=sqs
AWS_REGION=${AWS_REGION}
SQS_QUEUE_URL=${SQS_QUEUE_URL}
ARTIFACT_BACKEND=s3
S3_BUCKET_NAME=${S3_BUCKET_NAME}
LLM_REVIEW_ENABLED=${LLM_REVIEW_ENABLED}
BEDROCK_REVIEW_REGION=${BEDROCK_REVIEW_REGION}
BEDROCK_REVIEW_MODEL_ID=${BEDROCK_REVIEW_MODEL_ID}
WORKER_MAX_RECEIVE_COUNT=3
JUDGE_DOCKER_IMAGE=${JUDGE_DOCKER_IMAGE}
JUDGE_MAX_OUTPUT_BYTES=${JUDGE_MAX_OUTPUT_BYTES}
JUDGE_CONTAINER_STARTUP_GRACE_SECONDS=${JUDGE_CONTAINER_STARTUP_GRACE_SECONDS}
AUTO_CREATE_TABLES=false
AUTO_SEED=false
ENV

touch /var/log/hufsolve-worker.log

cat >/etc/systemd/system/hufsolve-worker.service <<'UNIT'
[Unit]
Description=HUFSOLVE Judge Worker
After=network-online.target docker.service
Wants=network-online.target
Requires=docker.service

[Service]
WorkingDirectory=/opt/hufsolve/app
ExecStart=/usr/bin/python3.11 -m worker.main
StandardOutput=append:/var/log/hufsolve-worker.log
StandardError=append:/var/log/hufsolve-worker.log
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT

if [[ -n "${CLOUDWATCH_LOG_GROUP}" ]]; then
  cat >/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json <<CWAGENT
{
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/log/hufsolve-worker.log",
            "log_group_name": "${CLOUDWATCH_LOG_GROUP}",
            "log_stream_name": "{instance_id}"
          }
        ]
      }
    }
  }
}
CWAGENT
  /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
    -a fetch-config \
    -m ec2 \
    -s \
    -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json
fi

systemctl daemon-reload
systemctl enable --now hufsolve-worker
