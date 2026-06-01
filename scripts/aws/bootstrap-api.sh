#!/usr/bin/env bash
set -euxo pipefail

: "${REPOSITORY_URL:?REPOSITORY_URL is required}"
: "${REPOSITORY_BRANCH:=main}"
: "${DATABASE_URL:=}"
: "${DATABASE_SECRET_ARN:=}"
: "${DATABASE_HOST:=}"
: "${SQS_QUEUE_URL:?SQS_QUEUE_URL is required}"
: "${S3_BUCKET_NAME:=}"
: "${FRONTEND_ORIGIN:=http://localhost:5173}"
: "${AWS_REGION:=ap-northeast-2}"
: "${CLOUDWATCH_LOG_GROUP:=}"

dnf update -y
dnf install -y amazon-cloudwatch-agent git python3.11 python3.11-pip

mkdir -p /opt/hufsolve
git clone --branch "${REPOSITORY_BRANCH}" "${REPOSITORY_URL}" /opt/hufsolve/app
cd /opt/hufsolve/app

python3.11 -m pip install --upgrade pip
python3.11 -m pip install -r backend/requirements.txt

if [[ -z "${DATABASE_URL}" ]]; then
  : "${DATABASE_SECRET_ARN:?DATABASE_SECRET_ARN is required when DATABASE_URL is empty}"
  : "${DATABASE_HOST:?DATABASE_HOST is required when DATABASE_URL is empty}"
  export AWS_REGION DATABASE_SECRET_ARN DATABASE_HOST
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
database = quote_plus(data["database"])
print(f"mysql+pymysql://{username}:{password}@{os.environ['DATABASE_HOST']}:3306/{database}")
PY
  )
fi

cat >/opt/hufsolve/app/.env <<ENV
APP_ENV=aws
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
BACKEND_CORS_ORIGINS=${FRONTEND_ORIGIN}
DATABASE_URL=${DATABASE_URL}
QUEUE_BACKEND=sqs
AWS_REGION=${AWS_REGION}
SQS_QUEUE_URL=${SQS_QUEUE_URL}
S3_BUCKET_NAME=${S3_BUCKET_NAME}
AUTO_CREATE_TABLES=true
AUTO_SEED=true
ENV

touch /var/log/hufsolve-api.log

cat >/etc/systemd/system/hufsolve-api.service <<'UNIT'
[Unit]
Description=HUFSOLVE FastAPI API Server
After=network-online.target
Wants=network-online.target

[Service]
WorkingDirectory=/opt/hufsolve/app
ExecStart=/usr/bin/python3.11 -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
StandardOutput=append:/var/log/hufsolve-api.log
StandardError=append:/var/log/hufsolve-api.log
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
            "file_path": "/var/log/hufsolve-api.log",
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
systemctl enable --now hufsolve-api
