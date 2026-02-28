#!/usr/bin/env python3
"""publish_release 辅助守卫：版本读取 + 发布白名单判定。"""

from __future__ import annotations

import argparse
import fnmatch
import subprocess
import sys
from pathlib import Path

VERSION_RE = r"^v[0-9]+\.[0-9]+\.[0-9]+([a-z0-9.-]+)?$"

ALLOWED_PATTERNS = [
    "VERSION",
    "CHANGELOG.md",
    "README.md",
    "README.zh-CN.md",
    "README.en.md",
    "LICENSE",
    ".gitignore",
    "scripts/*",
    "src/CloverSec-CTF-Build-Dockerizer/*",
    "docs/assets/readme/*",
    "Build_test/*",
    ".github/*",
]

BLOCKED_PATTERNS = [
    "internal/*",
    "dist/*",
    ".DS_Store",
    "*/.DS_Store",
    "SESSION_SUMMARY_v1.2.2.md",
    "*.pem",
    "*.key",
    ".env",
    ".env.*",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="publish guard")
    sub = parser.add_subparsers(dest="command", required=True)

    v = sub.add_parser("version", help="load/set version")
    v.add_argument("--version-file", required=True)
    v.add_argument("--override", default="")

    s = sub.add_parser("stage", help="collect stageable paths")
    s.add_argument("--root", required=True)
    return parser.parse_args()


def matches_any(path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(path, pat) for pat in patterns)


def cmd_version(version_file: Path, override: str) -> int:
    import re

    if override:
        version = override.strip()
        version_file.write_text(version + "\n", encoding="utf-8")
    else:
        if not version_file.exists():
            print(f"[ERROR] VERSION file not found: {version_file}", file=sys.stderr)
            return 1
        version = version_file.read_text(encoding="utf-8", errors="ignore").strip()

    if not version:
        print("[ERROR] Version is empty", file=sys.stderr)
        return 1
    if not re.match(VERSION_RE, version):
        print(f"[ERROR] Invalid VERSION format: {version}", file=sys.stderr)
        return 1
    print(version)
    return 0


def parse_porcelain_z(blob: bytes) -> list[str]:
    items = blob.split(b"\x00")
    out: list[str] = []
    idx = 0
    while idx < len(items):
        entry = items[idx]
        idx += 1
        if not entry:
            continue
        text = entry.decode("utf-8", errors="ignore")
        if len(text) < 4:
            continue
        status = text[:2]
        path = text[3:]
        out.append(path)
        if any(ch in status for ch in ("R", "C")) and idx < len(items):
            extra = items[idx]
            idx += 1
            if extra:
                out.append(extra.decode("utf-8", errors="ignore"))
    return out


def cmd_stage(root: Path) -> int:
    proc = subprocess.run(
        ["git", "-C", str(root), "status", "--porcelain", "-z"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        print(proc.stderr.decode("utf-8", errors="ignore"), file=sys.stderr)
        return 1

    changed_paths = parse_porcelain_z(proc.stdout)
    blocked: list[str] = []
    unexpected: list[str] = []
    allowed: list[str] = []

    for path in changed_paths:
        if matches_any(path, BLOCKED_PATTERNS):
            blocked.append(path)
            continue
        if not matches_any(path, ALLOWED_PATTERNS):
            unexpected.append(path)
            continue
        allowed.append(path)

    if blocked:
        print("[ERROR] 检测到阻断路径（不允许发布脚本自动提交）:", file=sys.stderr)
        for path in blocked:
            print(f"  - {path}", file=sys.stderr)
        return 3

    if unexpected:
        print("[ERROR] 检测到白名单外变更（请手动审查并提交）:", file=sys.stderr)
        for path in unexpected:
            print(f"  - {path}", file=sys.stderr)
        return 4

    dedup = sorted(set(allowed))
    for path in dedup:
        print(path)
    return 0


def main() -> int:
    args = parse_args()
    if args.command == "version":
        return cmd_version(Path(args.version_file).resolve(), args.override)
    if args.command == "stage":
        return cmd_stage(Path(args.root).resolve())
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
