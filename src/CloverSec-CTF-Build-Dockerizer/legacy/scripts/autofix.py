#!/usr/bin/env python3
"""Limited safe autofix for Dockerfile/start.sh used by validate.sh."""

from __future__ import annotations

import argparse
import difflib
import re
import sys
from pathlib import Path
from typing import List, Tuple


APT_INSTALL_RE = re.compile(r"apt-get\s+install\s+-y(?!\s+--no-install-recommends)")
APK_ADD_RE = re.compile(r"\bapk\s+add(?![^\n]*--no-cache)")
HAS_APT_CLEAN_RE = re.compile(r"rm\s+-rf\s+/var/lib/apt/lists/\*")
HAS_START_CHMOD_RE = re.compile(r"chmod[^\n]*/start\.sh")
HAS_FLAG_CHMOD_RE = re.compile(r"chmod[^\n]*/flag")

HOST_127_RE = re.compile(r"(--host(?:=|\s+))(127\.0\.0\.1|localhost)")
BIND_127_RE = re.compile(r"(-b\s+)(127\.0\.0\.1|localhost):")
RUNSERVER_127_RE = re.compile(r"(runserver\s+)(127\.0\.0\.1|localhost):")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply limited safe autofix for validate flow")
    parser.add_argument("--dockerfile", required=True, help="Path to Dockerfile")
    parser.add_argument("--start-sh", required=True, help="Path to start.sh")
    parser.add_argument("--challenge", default="", help="Optional challenge.yaml path")
    parser.add_argument("--write", action="store_true", help="Write changes to files")
    parser.add_argument(
        "--loopback",
        action="store_true",
        help="Allow replacing explicit loopback bind args with 0.0.0.0",
    )
    return parser.parse_args()


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception as exc:
        raise SystemExit(f"[ERROR] failed to read {path}: {exc}")


def write_text(path: Path, content: str) -> None:
    try:
        path.write_text(content, encoding="utf-8")
    except Exception as exc:
        raise SystemExit(f"[ERROR] failed to write {path}: {exc}")


def challenge_needs_flag(challenge_path: Path) -> bool:
    if not challenge_path.exists() or not challenge_path.is_file():
        return True

    try:
        import yaml
    except ModuleNotFoundError:
        # Keep conservative default if yaml parser is unavailable.
        return True

    try:
        raw = yaml.safe_load(challenge_path.read_text(encoding="utf-8")) or {}
    except Exception:
        return True

    if not isinstance(raw, dict):
        return True

    challenge = raw.get("challenge")
    if not isinstance(challenge, dict):
        return True

    if str(challenge.get("stack", "")).strip().lower() != "rdg":
        return True

    rdg = challenge.get("rdg")
    if not isinstance(rdg, dict):
        return True

    include_flag = rdg.get("include_flag_artifact", True)
    if isinstance(include_flag, bool):
        return include_flag
    if isinstance(include_flag, str):
        v = include_flag.strip().lower()
        if v in {"false", "0", "no", "n"}:
            return False
        if v in {"true", "1", "yes", "y"}:
            return True
    return True


def apply_dockerfile_fixes(content: str, need_flag: bool) -> Tuple[str, List[str]]:
    fixes: List[str] = []
    updated = content

    new_updated = APT_INSTALL_RE.sub("apt-get install -y --no-install-recommends", updated)
    if new_updated != updated:
        updated = new_updated
        fixes.append("apt-get install: added --no-install-recommends")

    new_updated = APK_ADD_RE.sub("apk add --no-cache", updated)
    if new_updated != updated:
        updated = new_updated
        fixes.append("apk add: added --no-cache")

    if "apt-get install" in updated and not HAS_APT_CLEAN_RE.search(updated):
        suffix = "\nRUN rm -rf /var/lib/apt/lists/*\n"
        if not updated.endswith("\n"):
            updated += "\n"
        updated += suffix
        fixes.append("added apt cache cleanup line")

    if not HAS_START_CHMOD_RE.search(updated):
        if not updated.endswith("\n"):
            updated += "\n"
        updated += "RUN chmod 555 /start.sh\n"
        fixes.append("added chmod 555 /start.sh")

    if need_flag and not HAS_FLAG_CHMOD_RE.search(updated):
        if not updated.endswith("\n"):
            updated += "\n"
        updated += "RUN chmod 444 /flag\n"
        fixes.append("added chmod 444 /flag")

    return updated, fixes


def apply_start_fixes(content: str, enable_loopback_fix: bool) -> Tuple[str, List[str]]:
    fixes: List[str] = []
    updated = content

    if not enable_loopback_fix:
        return updated, fixes

    new_updated = HOST_127_RE.sub(r"\g<1>0.0.0.0", updated)
    if new_updated != updated:
        updated = new_updated
        fixes.append("rewrote --host 127.0.0.1/localhost -> 0.0.0.0")

    new_updated = BIND_127_RE.sub(r"\g<1>0.0.0.0:", updated)
    if new_updated != updated:
        updated = new_updated
        fixes.append("rewrote -b 127.0.0.1/localhost -> 0.0.0.0")

    new_updated = RUNSERVER_127_RE.sub(r"\g<1>0.0.0.0:", updated)
    if new_updated != updated:
        updated = new_updated
        fixes.append("rewrote runserver 127.0.0.1/localhost -> 0.0.0.0")

    return updated, fixes


def print_diff(path: Path, old: str, new: str) -> None:
    diff = difflib.unified_diff(
        old.splitlines(keepends=True),
        new.splitlines(keepends=True),
        fromfile=f"{path}",
        tofile=f"{path}",
    )
    text = "".join(diff)
    if text.strip():
        print(text, end="" if text.endswith("\n") else "\n")


def main() -> int:
    args = parse_args()

    docker_path = Path(args.dockerfile).resolve()
    start_path = Path(args.start_sh).resolve()
    challenge_path = Path(args.challenge).resolve() if args.challenge else Path("/nonexistent")

    if not docker_path.exists():
        print(f"[ERROR] Dockerfile not found: {docker_path}", file=sys.stderr)
        return 2
    if not start_path.exists():
        print(f"[ERROR] start.sh not found: {start_path}", file=sys.stderr)
        return 2

    docker_old = read_text(docker_path)
    start_old = read_text(start_path)

    need_flag = challenge_needs_flag(challenge_path)

    docker_new, docker_fixes = apply_dockerfile_fixes(docker_old, need_flag)
    start_new, start_fixes = apply_start_fixes(start_old, args.loopback)

    any_changes = docker_new != docker_old or start_new != start_old

    print("[AUTOFIX] mode={}".format("write" if args.write else "dry-run"))
    if args.loopback:
        print("[AUTOFIX] loopback rewrite enabled")

    if docker_fixes:
        print("[AUTOFIX] Dockerfile fixes:")
        for item in docker_fixes:
            print(f"  - {item}")

    if start_fixes:
        print("[AUTOFIX] start.sh fixes:")
        for item in start_fixes:
            print(f"  - {item}")

    if any_changes:
        print_diff(docker_path, docker_old, docker_new)
        print_diff(start_path, start_old, start_new)
        if args.write:
            write_text(docker_path, docker_new)
            write_text(start_path, start_new)
            print("[AUTOFIX] changes written")
        else:
            print("[AUTOFIX] dry-run only (no file changes)")
    else:
        print("[AUTOFIX] no safe fixes applicable")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
