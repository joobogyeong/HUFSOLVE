from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str
    required: bool


def command_check(
    name: str,
    command: list[str],
    required: bool,
) -> CheckResult:
    executable = resolve_executable(command[0])
    if executable is None:
        return CheckResult(
            name=name,
            ok=False,
            detail=f"{command[0]} command not found",
            required=required,
        )

    try:
        completed = subprocess.run(
            [executable, *command[1:]],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except Exception as exc:
        return CheckResult(name=name, ok=False, detail=str(exc), required=required)

    output = (completed.stdout or completed.stderr).strip()
    return CheckResult(
        name=name,
        ok=completed.returncode == 0,
        detail=output,
        required=required,
    )


def resolve_executable(name: str) -> str | None:
    executable = shutil.which(name)
    if executable is not None:
        return executable

    if os.name == "nt" and name == "aws":
        default_aws_cli = Path(r"C:\Program Files\Amazon\AWSCLIV2\aws.exe")
        if default_aws_cli.exists():
            return str(default_aws_cli)

    return None


def file_check(path: str, required: bool = True) -> CheckResult:
    exists = Path(path).exists()
    return CheckResult(
        name=f"file:{path}",
        ok=exists,
        detail="found" if exists else "missing",
        required=required,
    )


def run_checks(mode: str) -> list[CheckResult]:
    docker_required = mode == "local"
    checks = [
        CheckResult(
            name="python",
            ok=sys.version_info >= (3, 11),
            detail=sys.version.split()[0],
            required=True,
        ),
        command_check("docker-cli", ["docker", "--version"], required=docker_required),
        command_check(
            "docker-daemon",
            ["docker", "info", "--format", "{{.ServerVersion}}"],
            required=docker_required,
        ),
        file_check("docker/python-runner/Dockerfile"),
        file_check("backend/requirements.txt"),
        file_check("worker/requirements.txt"),
    ]

    if mode == "aws":
        checks.extend(
            [
                command_check("aws-cli", ["aws", "--version"], required=True),
                file_check("infra/aws/cloudformation/hufsolve-core.yaml"),
                file_check("infra/aws/parameters.local.json"),
            ]
        )

    return checks


def main() -> None:
    parser = argparse.ArgumentParser(description="HUFSOLVE environment preflight")
    parser.add_argument("--mode", choices=["local", "aws"], default="local")
    args = parser.parse_args()

    checks = run_checks(args.mode)
    ok = all(check.ok or not check.required for check in checks)
    print(
        json.dumps(
            {
                "mode": args.mode,
                "ok": ok,
                "checks": [asdict(check) for check in checks],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
