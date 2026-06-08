#!/usr/bin/env bash
set -euo pipefail

: "${REPOSITORY_URL:?REPOSITORY_URL is required}"
: "${REPOSITORY_BRANCH:=main}"
: "${DATABASE_URL:=}"
: "${DATABASE_SECRET_ARN:=}"
: "${DATABASE_HOST:=}"
: "${DATABASE_NAME:=hufsolve}"
: "${SMTP_SECRET_ARN:=}"
: "${SQS_QUEUE_URL:?SQS_QUEUE_URL is required}"
: "${S3_BUCKET_NAME:?S3_BUCKET_NAME is required}"
: "${FRONTEND_ORIGIN:=http://localhost:5173}"
: "${AWS_REGION:=ap-northeast-2}"
: "${LLM_REVIEW_ENABLED:=false}"
: "${BEDROCK_REVIEW_REGION:=ap-northeast-2}"
: "${BEDROCK_REVIEW_MODEL_ID:=global.amazon.nova-2-lite-v1:0}"
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

if [[ -n "${SMTP_SECRET_ARN}" ]]; then
  export AWS_REGION SMTP_SECRET_ARN
  python3.11 - <<'PY'
import json
import os
from pathlib import Path

import boto3

secret = boto3.client("secretsmanager", region_name=os.environ["AWS_REGION"]).get_secret_value(
    SecretId=os.environ["SMTP_SECRET_ARN"]
)
data = json.loads(secret["SecretString"])
required = ("SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD", "SMTP_FROM")
missing = [key for key in required if not str(data.get(key, "")).strip()]
if missing:
    raise RuntimeError(f"SMTP secret is missing required keys: {', '.join(missing)}")

lines = [f"{key}={json.dumps(str(data[key]), ensure_ascii=False)}" for key in required]
Path("/tmp/hufsolve-smtp-env").write_text("\n".join(lines) + "\n", encoding="utf-8")
Path("/tmp/hufsolve-smtp-env").chmod(0o600)
PY
fi

install -m 600 /dev/null /opt/hufsolve/app/.env
cat >/opt/hufsolve/app/.env <<ENV
APP_ENV=aws
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
BACKEND_CORS_ORIGINS=${FRONTEND_ORIGIN}
DATABASE_URL=${DATABASE_URL}
QUEUE_BACKEND=sqs
AWS_REGION=${AWS_REGION}
SQS_QUEUE_URL=${SQS_QUEUE_URL}
ARTIFACT_BACKEND=s3
S3_BUCKET_NAME=${S3_BUCKET_NAME}
LLM_REVIEW_ENABLED=${LLM_REVIEW_ENABLED}
BEDROCK_REVIEW_REGION=${BEDROCK_REVIEW_REGION}
BEDROCK_REVIEW_MODEL_ID=${BEDROCK_REVIEW_MODEL_ID}
AUTO_CREATE_TABLES=false
AUTO_SEED=false
ENV
if [[ -f /tmp/hufsolve-smtp-env ]]; then
  cat /tmp/hufsolve-smtp-env >>/opt/hufsolve/app/.env
  rm -f /tmp/hufsolve-smtp-env
fi

python3.11 -m backend.app.bootstrap --seed-if-empty

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
