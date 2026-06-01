#!/usr/bin/env bash
set -euxo pipefail

: "${ECR_REPOSITORY_URI:?ECR_REPOSITORY_URI is required}"
: "${AWS_REGION:=ap-northeast-2}"
: "${RUNNER_IMAGE_TAG:=3.11}"

LOCAL_IMAGE="judge-python:${RUNNER_IMAGE_TAG}"
REMOTE_IMAGE="${ECR_REPOSITORY_URI}:${RUNNER_IMAGE_TAG}"
REGISTRY_HOST="${ECR_REPOSITORY_URI%%/*}"

aws ecr get-login-password --region "${AWS_REGION}" |
  docker login --username AWS --password-stdin "${REGISTRY_HOST}"
docker build -t "${LOCAL_IMAGE}" docker/python-runner
docker tag "${LOCAL_IMAGE}" "${REMOTE_IMAGE}"
docker push "${REMOTE_IMAGE}"

printf 'Published %s\n' "${REMOTE_IMAGE}"
