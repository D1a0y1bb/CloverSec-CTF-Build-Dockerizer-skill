#!/usr/bin/env python3
"""Create Docker build/run/save/load artifact metadata for CTF deliveries."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None


SAFE_IMAGE_RE = re.compile(r"[^a-zA-Z0-9_.:/-]+")
DEFAULT_PLATFORM = "linux/amd64"


def read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists() or yaml is None:
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


def challenge_root(data: dict[str, Any]) -> dict[str, Any]:
    challenge = data.get("challenge")
    return challenge if isinstance(challenge, dict) else data


def nested_dict(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    return value if isinstance(value, dict) else {}


def normalize_image_name(value: str) -> str:
    text = SAFE_IMAGE_RE.sub("-", value.strip().lower()).strip("-")
    return text or "cloversec-ctf-challenge:latest"


def normalize_port(value: str) -> tuple[str, str, str]:
    text = str(value).strip()
    if not text:
        raise ValueError("empty port")
    if ":" in text:
        host, container = text.split(":", 1)
    else:
        host = container = text
    if not host.isdigit() or not container.isdigit():
        raise ValueError(f"invalid port mapping: {value}")
    return host, container, f"{host}:{container}"


def port_mappings(cli_ports: list[str], challenge: dict[str, Any]) -> list[dict[str, str]]:
    values = list(cli_ports)
    if not values:
        expose_ports = challenge.get("expose_ports")
        if isinstance(expose_ports, list):
            values.extend(str(item) for item in expose_ports if str(item).strip())
    mappings: list[dict[str, str]] = []
    for value in values:
        host, container, mapping = normalize_port(value)
        mappings.append({"host": host, "container": container, "mapping": mapping})
    return mappings


def command_text(command: list[str]) -> str:
    return shlex.join(command)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_plan(args: argparse.Namespace) -> dict[str, Any]:
    project_dir = Path(args.project_dir).resolve()
    challenge_path = Path(args.config).resolve() if args.config else project_dir / "challenge.yaml"
    challenge = challenge_root(read_yaml(challenge_path))
    platform_cfg = nested_dict(challenge, "platform")

    platform = str(args.platform or platform_cfg.get("docker_platform") or DEFAULT_PLATFORM).strip()
    image_name = normalize_image_name(args.image_name or f"cloversec/{project_dir.name}:latest")
    tar_path = Path(args.tar_path).resolve() if args.tar_path else project_dir / f"{image_name.split('/')[-1].replace(':', '-')}.tar"
    container_name = normalize_image_name(args.container_name or f"{project_dir.name}-ctf").replace("/", "-").replace(":", "-")
    ports = port_mappings(args.port or [], challenge)
    container_tar = Path(args.container_tar_path).resolve() if args.container_tar_path else None

    build_cmd = ["docker", "build", "--platform", platform, "-t", image_name, str(project_dir)]
    run_cmd = ["docker", "run", "-d", "--name", container_name]
    for item in ports:
        run_cmd.extend(["-p", item["mapping"]])
    run_cmd.extend([image_name, "/start.sh"])
    save_cmd = ["docker", "save", "-o", str(tar_path), image_name]
    load_cmd = ["docker", "load", "-i", str(tar_path)]
    inspect_cmd = ["docker", "image", "inspect", image_name]

    commands: dict[str, str] = {
        "build": command_text(build_cmd),
        "run": command_text(run_cmd),
        "save_image_tar": command_text(save_cmd),
        "load_image_tar": command_text(load_cmd),
        "inspect_image": command_text(inspect_cmd),
    }
    if container_tar is not None:
        commands["export_container_tar"] = command_text(["docker", "export", "-o", str(container_tar), container_name])
        commands["import_container_tar"] = command_text(["docker", "import", str(container_tar), image_name + "-imported"])

    output = {
        "schema_version": "1.0",
        "environment": {
            "project_dir": str(project_dir),
            "challenge_path": str(challenge_path),
            "docker_platform_expected": platform,
            "entrypoint": "/start.sh",
            "ports": ports,
        },
        "docker_artifacts": {
            "image_name": image_name,
            "container_name": container_name,
            "image_tar_path": str(tar_path),
            "container_tar_path": str(container_tar) if container_tar else "",
            "platform_expected": platform,
            "commands": commands,
            "status": "planned",
        },
        "xlsx_fields": {
            "构建状态": "未执行",
            "环境包/附件包路径": str(tar_path),
            "开放端口": ",".join(item["container"] for item in ports),
            "备注": f"docker_platform={platform}; image={image_name}",
        },
    }
    return output


def write_json(path: str | None, data: dict[str, Any]) -> None:
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    if path:
        Path(path).write_text(text, encoding="utf-8")
    else:
        print(text, end="")


def run_shell(command: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=str(cwd), shell=True, text=True, capture_output=True, check=False)


def execute_plan(args: argparse.Namespace) -> int:
    plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    project_dir = Path(plan["environment"]["project_dir"]).resolve()
    commands = plan["docker_artifacts"]["commands"]
    results = []
    for step in args.steps.split(","):
        step = step.strip()
        if not step:
            continue
        if step not in commands:
            print(f"unknown step: {step}", file=sys.stderr)
            return 2
        proc = run_shell(commands[step], project_dir)
        results.append(
            {
                "step": step,
                "command": commands[step],
                "returncode": proc.returncode,
                "stdout": proc.stdout[-4000:],
                "stderr": proc.stderr[-4000:],
            }
        )
        if proc.returncode != 0 and not args.continue_on_error:
            break
    plan["docker_artifacts"]["execution"] = results
    plan["docker_artifacts"]["status"] = "executed" if all(item["returncode"] == 0 for item in results) else "failed"
    tar_path = Path(plan["docker_artifacts"].get("image_tar_path", ""))
    if tar_path.exists() and tar_path.is_file():
        plan["docker_artifacts"]["image_tar_sha256"] = sha256_file(tar_path)
        plan["xlsx_fields"]["环境包/附件包路径"] = str(tar_path)
    write_json(args.output, plan)
    return 0 if plan["docker_artifacts"]["status"] == "executed" else 1


def platform_from_inspect(data: Any) -> str:
    if isinstance(data, list) and data:
        first = data[0]
        if isinstance(first, dict):
            os_name = str(first.get("Os") or first.get("OS") or "").strip()
            arch = str(first.get("Architecture") or "").strip()
            variant = str(first.get("Variant") or "").strip()
            if os_name and arch:
                return f"{os_name}/{arch}" + (f"/{variant}" if variant else "")
    return ""


def validate_artifacts(args: argparse.Namespace) -> int:
    plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    expected = str(plan["docker_artifacts"].get("platform_expected") or DEFAULT_PLATFORM)
    inspect_path = Path(args.inspect_json) if args.inspect_json else None
    issues: list[str] = []
    actual = ""
    if inspect_path and inspect_path.exists():
        actual = platform_from_inspect(json.loads(inspect_path.read_text(encoding="utf-8")))
        if actual != expected:
            issues.append(f"platform mismatch: expected {expected}, got {actual or 'unknown'}")
    tar_path = Path(plan["docker_artifacts"].get("image_tar_path", ""))
    if tar_path.exists() and tar_path.is_file():
        plan["docker_artifacts"]["image_tar_sha256"] = sha256_file(tar_path)
    else:
        issues.append(f"image tar missing: {tar_path}")
    plan["docker_artifacts"]["platform_actual"] = actual
    plan["docker_artifacts"]["status"] = "validated" if not issues else "validation_failed"
    plan["docker_artifacts"]["issues"] = issues
    plan["xlsx_fields"]["构建状态"] = "已构建" if not issues else "验证失败"
    write_json(args.output, plan)
    return 0 if not issues else 1


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Docker artifact planner and validator")
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan_parser = subparsers.add_parser("plan", help="write docker artifact plan")
    plan_parser.add_argument("--project-dir", required=True)
    plan_parser.add_argument("--config")
    plan_parser.add_argument("--image-name")
    plan_parser.add_argument("--container-name")
    plan_parser.add_argument("--platform", default=DEFAULT_PLATFORM)
    plan_parser.add_argument("--tar-path")
    plan_parser.add_argument("--container-tar-path")
    plan_parser.add_argument("--port", action="append")
    plan_parser.add_argument("--output")

    exec_parser = subparsers.add_parser("execute", help="execute selected docker steps from a plan")
    exec_parser.add_argument("--plan", required=True)
    exec_parser.add_argument("--steps", default="build,run,save_image_tar,inspect_image")
    exec_parser.add_argument("--continue-on-error", action="store_true")
    exec_parser.add_argument("--output")

    validate_parser = subparsers.add_parser("validate-artifacts", help="validate amd64 metadata and tar file")
    validate_parser.add_argument("--plan", required=True)
    validate_parser.add_argument("--inspect-json")
    validate_parser.add_argument("--output")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.command == "plan":
        write_json(args.output, build_plan(args))
        return 0
    if args.command == "execute":
        return execute_plan(args)
    if args.command == "validate-artifacts":
        return validate_artifacts(args)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
