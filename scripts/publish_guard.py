#!/usr/bin/env python3
"""publish_release 辅助守卫：版本读取 + 发布白名单判定。"""

from __future__ import annotations

import argparse
import fnmatch
import re
import subprocess
import sys
from pathlib import Path

VERSION_RE = r"^v[0-9]+\.[0-9]+\.[0-9]+([a-z0-9.-]+)?$"
VERSION_CAPTURE_RE = r"v[0-9]+\.[0-9]+\.[0-9]+(?:[a-z0-9.-]+)?"

REQUIRED_READMES = ("README.md", "README.en.md", "README.ja.md", "README.zh-CN.md")
FULL_READMES = ("README.md", "README.en.md", "README.ja.md")

ALLOWED_PATTERNS = [
    "VERSION",
    "CHANGELOG.md",
    "README.md",
    "README.zh-CN.md",
    "README.ja.md",
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


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def extract_readme_version(text: str) -> str:
    patterns = [
        rf"^\s*VERSION[：:]\s*({VERSION_CAPTURE_RE})\s*$",
        rf"<strong>\s*VERSION\s*</strong>\s*[：:]\s*({VERSION_CAPTURE_RE})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
        if match:
            return match.group(1).strip()
    return ""


def has_readme_link(text: str, target: str) -> bool:
    return f"({target})" in text or f'href="{target}"' in text


def ensure_publish_docs(root: Path) -> int:
    version_file = root / "VERSION"
    if not version_file.exists():
        print(f"[ERROR] VERSION 文件缺失：{version_file}", file=sys.stderr)
        return 5

    repo_version = version_file.read_text(encoding="utf-8", errors="ignore").strip()
    if not repo_version:
        print("[ERROR] VERSION 为空", file=sys.stderr)
        return 5

    texts: dict[str, str] = {}
    errors: list[str] = []

    for name in REQUIRED_READMES:
        path = root / name
        if not path.exists():
            errors.append(f"缺少 README 文件：{name}")
            continue
        texts[name] = read_text(path)

    for name in FULL_READMES:
        text = texts.get(name)
        if text is None:
            continue
        version = extract_readme_version(text)
        if not version:
            errors.append(f"{name} 缺少可解析 VERSION 元信息")
        elif version != repo_version:
            errors.append(f"{name} VERSION({version}) 与 VERSION({repo_version}) 不一致")

    en_text = texts.get("README.en.md", "")
    if re.search(r"^#\s*Legacy English Entry\s*$", en_text, flags=re.MULTILINE):
        errors.append("README.en.md 仍为 Legacy English Entry 短页")

    zh_compat = texts.get("README.zh-CN.md", "")
    if zh_compat:
        if not has_readme_link(zh_compat, "README.md"):
            errors.append("README.zh-CN.md 未链接 README.md")
        if "兼容" not in zh_compat:
            errors.append("README.zh-CN.md 未体现兼容入口定位")

    for name in ("README.md", "README.en.md", "README.ja.md"):
        text = texts.get(name, "")
        for target in ("README.md", "README.en.md", "README.ja.md", "README.zh-CN.md"):
            if name == target:
                continue
            if not has_readme_link(text, target):
                errors.append(f"{name} 缺少语言互链：{target}")

    if errors:
        print("[ERROR] 发布前 README 守卫失败：", file=sys.stderr)
        for item in errors:
            print(f"  - {item}", file=sys.stderr)
        return 5
    return 0


def cmd_stage(root: Path) -> int:
    guard_rc = ensure_publish_docs(root)
    if guard_rc != 0:
        return guard_rc

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
