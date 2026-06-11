#!/usr/bin/env python3
"""Collect local platform facts used by release and manual validation."""

from __future__ import annotations

import argparse
import json
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Platform compatibility matrix check")
    parser.add_argument("--profile", choices=("dev", "release", "linux-qemu"), default="dev")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--output", help="optional JSON output path")
    return parser.parse_args()


def run(cmd: list[str], timeout: int = 15) -> dict[str, Any]:
    try:
        proc = subprocess.run(cmd, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout)
        return {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout": proc.stdout.strip()[-2000:],
            "stderr": proc.stderr.strip()[-2000:],
        }
    except FileNotFoundError:
        return {"ok": False, "returncode": 127, "stdout": "", "stderr": "not found"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "returncode": 124, "stdout": "", "stderr": "timeout"}


def tool_info(name: str, version_cmd: list[str]) -> dict[str, Any]:
    path = shutil.which(name)
    info: dict[str, Any] = {"available": bool(path), "path": path or ""}
    if path:
        info["version"] = run(version_cmd)
    return info


def docker_info() -> dict[str, Any]:
    info = tool_info("docker", ["docker", "--version"])
    if info["available"]:
        info["daemon"] = run(["docker", "info", "--format", "server={{.ServerVersion}} os={{.OSType}} arch={{.Architecture}}"], timeout=20)
        info["compose"] = run(["docker", "compose", "version"], timeout=20)
        info["sbom"] = run(["docker", "sbom", "--help"], timeout=20)
    return info


def build_payload(profile_name: str) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "profile": profile_name,
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python": sys.version.split()[0],
        },
        "tools": {
            "bash": tool_info("bash", ["bash", "--version"]),
            "git": tool_info("git", ["git", "--version"]),
            "python3": tool_info("python3", ["python3", "--version"]),
            "docker": docker_info(),
            "qemu_system_x86_64": tool_info("qemu-system-x86_64", ["qemu-system-x86_64", "--version"]),
            "qemu_img": tool_info("qemu-img", ["qemu-img", "--version"]),
            "syft": tool_info("syft", ["syft", "--version"]),
        },
        "checks": [],
    }
    add_checks(payload)
    return payload


def add_check(payload: dict[str, Any], name: str, ok: bool, required: bool, detail: str = "") -> None:
    payload["checks"].append({"name": name, "ok": bool(ok), "required": bool(required), "detail": detail})


def command_ok(payload: dict[str, Any], path: str, nested: list[str] | None = None) -> bool:
    cur: Any = payload
    for item in path.split("."):
        cur = cur.get(item) if isinstance(cur, dict) else None
    if nested:
        for item in nested:
            cur = cur.get(item) if isinstance(cur, dict) else None
    if isinstance(cur, dict) and "ok" in cur:
        return bool(cur.get("ok"))
    return bool(cur)


def add_checks(payload: dict[str, Any]) -> None:
    profile_name = payload["profile"]
    tools = payload["tools"]
    add_check(payload, "python3_available", bool(tools["python3"]["available"]), True)
    add_check(payload, "bash_available", bool(tools["bash"]["available"]), True)
    add_check(payload, "git_available", bool(tools["git"]["available"]), True)

    docker_required = profile_name in {"release", "linux-qemu"}
    docker_available = bool(tools["docker"]["available"])
    docker_daemon_ok = command_ok(payload, "tools.docker.daemon")
    add_check(payload, "docker_cli_available", docker_available, docker_required)
    add_check(payload, "docker_daemon_reachable", docker_daemon_ok, docker_required)

    compose_ok = command_ok(payload, "tools.docker.compose")
    add_check(payload, "docker_compose_available", compose_ok, profile_name == "release")

    syft_available = bool(tools["syft"]["available"])
    docker_sbom_ok = command_ok(payload, "tools.docker.sbom")
    add_check(payload, "sbom_tool_available", syft_available or docker_sbom_ok, False, "syft preferred; docker sbom accepted")

    qemu_required = profile_name == "linux-qemu"
    add_check(payload, "qemu_system_x86_64_available", bool(tools["qemu_system_x86_64"]["available"]), qemu_required)
    add_check(payload, "qemu_img_available", bool(tools["qemu_img"]["available"]), qemu_required)

    payload["ok"] = all(check["ok"] for check in payload["checks"] if check["required"])


def main() -> int:
    args = parse_args()
    payload = build_payload(args.profile)
    if args.output:
        out = Path(args.output).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        status = "OK" if payload["ok"] else "FAIL"
        print(f"Platform matrix: {status}")
        print(f"- profile: {payload['profile']}")
        print(f"- system: {payload['platform']['system']} {payload['platform']['release']} {payload['platform']['machine']}")
        for check in payload["checks"]:
            mark = "OK" if check["ok"] else "FAIL"
            req = "required" if check["required"] else "optional"
            detail = f" - {check['detail']}" if check.get("detail") else ""
            print(f"  - {check['name']}: {mark} ({req}){detail}")

    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
