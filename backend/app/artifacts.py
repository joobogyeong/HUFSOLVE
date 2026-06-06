from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any, Protocol

from .config import settings


class ArtifactStore(Protocol):
    def put_bytes(self, key: str, data: bytes, content_type: str) -> str: ...

    def get_bytes(self, key: str) -> bytes: ...

    def exists(self, key: str) -> bool: ...


class LocalArtifactStore:
    def __init__(self, root: str) -> None:
        self._root = Path(root).resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    def put_bytes(self, key: str, data: bytes, content_type: str) -> str:
        path = self._path_for(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return key

    def get_bytes(self, key: str) -> bytes:
        return self._path_for(key).read_bytes()

    def exists(self, key: str) -> bool:
        return self._path_for(key).is_file()

    def _path_for(self, key: str) -> Path:
        normalized = PurePosixPath(key)
        if normalized.is_absolute() or ".." in normalized.parts:
            raise ValueError(f"Invalid artifact key: {key}")

        path = (self._root / Path(*normalized.parts)).resolve()
        if self._root != path and self._root not in path.parents:
            raise ValueError(f"Artifact key escapes local root: {key}")
        return path


class S3ArtifactStore:
    def __init__(self, bucket_name: str, region_name: str) -> None:
        if not bucket_name:
            raise RuntimeError("S3_BUCKET_NAME is required when ARTIFACT_BACKEND=s3")

        import boto3

        self._bucket_name = bucket_name
        self._client = boto3.client("s3", region_name=region_name)

    def put_bytes(self, key: str, data: bytes, content_type: str) -> str:
        self._client.put_object(
            Bucket=self._bucket_name,
            Key=key,
            Body=data,
            ContentType=content_type,
            ServerSideEncryption="AES256",
        )
        return key

    def get_bytes(self, key: str) -> bytes:
        response = self._client.get_object(Bucket=self._bucket_name, Key=key)
        return response["Body"].read()

    def exists(self, key: str) -> bool:
        response = self._client.list_objects_v2(
            Bucket=self._bucket_name,
            Prefix=key,
            MaxKeys=1,
        )
        return any(item["Key"] == key for item in response.get("Contents", []))


_artifact_store: ArtifactStore | None = None


def get_artifact_store() -> ArtifactStore:
    global _artifact_store
    if _artifact_store is None:
        if settings.artifact_backend == "s3":
            _artifact_store = S3ArtifactStore(settings.s3_bucket_name, settings.aws_region)
        elif settings.artifact_backend == "local":
            _artifact_store = LocalArtifactStore(settings.artifact_local_dir)
        else:
            raise RuntimeError(f"Unsupported ARTIFACT_BACKEND: {settings.artifact_backend}")
    return _artifact_store


def put_text(key: str, value: str) -> tuple[str, str]:
    data = value.encode("utf-8")
    return get_artifact_store().put_bytes(key, data, "text/plain; charset=utf-8"), sha256(data)


def put_json(key: str, value: Any) -> tuple[str, str]:
    data = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return get_artifact_store().put_bytes(key, data, "application/json"), sha256(data)


def get_text(key: str) -> str:
    return get_artifact_store().get_bytes(key).decode("utf-8")


def get_json(key: str) -> Any:
    return json.loads(get_artifact_store().get_bytes(key))


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
