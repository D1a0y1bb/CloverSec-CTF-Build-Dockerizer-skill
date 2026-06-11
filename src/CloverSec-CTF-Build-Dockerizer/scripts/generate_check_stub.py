#!/usr/bin/env python3
"""Generate editable RDG/SecOps check-service stubs."""

from __future__ import annotations

import argparse
import os
import shlex
import sys
from pathlib import Path
from typing import Dict

SCRIPT_DIR = Path(__file__).resolve().parent

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from result_utils import dump_json, structured_ok  # noqa: E402

SUPPORTED_TYPES = {"http", "tcp", "redis", "mysql", "ssh"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate editable check-service script stubs")
    parser.add_argument("--type", required=True, choices=sorted(SUPPORTED_TYPES), help="check type")
    parser.add_argument("--output", required=True, help="output check script path")
    parser.add_argument("--target-port", default="", help="default target port")
    parser.add_argument("--path", default="/", help="HTTP path")
    parser.add_argument("--method", default="GET", help="HTTP method")
    parser.add_argument("--expect-status", default="", help="HTTP expected status code")
    parser.add_argument("--expect-text", default="", help="HTTP body text expectation")
    parser.add_argument("--expect-header", default="", help="HTTP header text expectation")
    parser.add_argument("--forbid-text", default="", help="HTTP body text that must not appear")
    parser.add_argument("--forbid-header", default="", help="HTTP header text that must not appear")
    parser.add_argument("--redis-key", default="", help="Redis key to read")
    parser.add_argument("--redis-expect-value", default="", help="Expected Redis value for --redis-key")
    parser.add_argument("--mysql-query", default="", help="MySQL query to execute")
    parser.add_argument("--mysql-expect-text", default="", help="Expected text in MySQL query result")
    parser.add_argument("--ssh-expect-banner", default="SSH-", help="SSH banner prefix/text expectation")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser.parse_args()


def default_port(check_type: str, explicit: str) -> str:
    if explicit:
        return explicit
    return {
        "http": "80",
        "tcp": "80",
        "redis": "6379",
        "mysql": "3306",
        "ssh": "22",
    }[check_type]


def header(port: str) -> str:
    return f"""#!/bin/bash
set -euo pipefail

# CHECK_REVIEW_REQUIRED: edit this generated check before delivery.
# Contract: bash check/check.sh [target_ip] [target_port]
# Exit code: 0=pass, 1=service failed, 2=usage/runtime error.

TARGET_IP="${{1:-${{TARGET_IP:-${{TARGET_HOST:-127.0.0.1}}}}}}"
TARGET_PORT="${{2:-${{TARGET_PORT:-{port}}}}}"

log() {{
  printf '[CHECK] %s\\n' "$1" >&2
}}

if [[ -z "$TARGET_IP" || -z "$TARGET_PORT" ]]; then
  log "usage: bash check/check.sh [target_ip] [target_port]"
  exit 2
fi

"""


def tcp_body() -> str:
    return """if timeout 5 bash -lc "cat < /dev/null > /dev/tcp/${TARGET_IP}/${TARGET_PORT}" 2>/dev/null; then
  log "tcp reachable: ${TARGET_IP}:${TARGET_PORT}"
  exit 0
fi

log "tcp unreachable: ${TARGET_IP}:${TARGET_PORT}"
exit 1
"""


def http_body(
    path: str,
    method: str,
    expect_status: str,
    expect_text: str,
    expect_header: str,
    forbid_text: str,
    forbid_header: str,
) -> str:
    quoted_path = shlex.quote(path or "/")
    quoted_method = shlex.quote((method or "GET").upper())
    status_block = ""
    if expect_status:
        status_block = f"""
if [[ "$status_code" != {shlex.quote(expect_status)} ]]; then
  log "unexpected HTTP status: $status_code"
  exit 1
fi
"""
    else:
        status_block = """
if [[ "$status_code" -ge 400 ]]; then
  log "HTTP status indicates failure: $status_code"
  exit 1
fi
"""
    text_block = ""
    if expect_text:
        text_block = f"""
if ! grep -Fq {shlex.quote(expect_text)} "$body_file"; then
  log "expected body text not found"
  exit 1
fi
"""
    forbid_text_block = ""
    if forbid_text:
        forbid_text_block = f"""
if grep -Fq {shlex.quote(forbid_text)} "$body_file"; then
  log "forbidden body text observed"
  exit 1
fi
"""
    header_block = ""
    if expect_header:
        header_block = f"""
if ! grep -Fqi {shlex.quote(expect_header)} "$header_file"; then
  log "expected header text not found"
  exit 1
fi
"""
    forbid_header_block = ""
    if forbid_header:
        forbid_header_block = f"""
if grep -Fqi {shlex.quote(forbid_header)} "$header_file"; then
  log "forbidden header text observed"
  exit 1
fi
"""
    return f"""CHECK_PATH={quoted_path}
CHECK_METHOD={quoted_method}
body_file="$(mktemp)"
header_file="$(mktemp)"
trap 'rm -f "$body_file" "$header_file"' EXIT

status_code="$(curl -sS --max-time 5 -X "$CHECK_METHOD" -D "$header_file" -o "$body_file" -w '%{{http_code}}' "http://${{TARGET_IP}}:${{TARGET_PORT}}${{CHECK_PATH}}" || true)"
if [[ -z "$status_code" || "$status_code" == "000" ]]; then
  log "http request failed"
  exit 1
fi
{status_block}{text_block}{forbid_text_block}{header_block}{forbid_header_block}
log "http check passed"
exit 0
"""


def redis_body(redis_key: str, redis_expect_value: str) -> str:
    return (
        f"REDIS_KEY={shlex.quote(redis_key)}\n"
        f"REDIS_EXPECT_VALUE={shlex.quote(redis_expect_value)}\n\n"
        """if command -v redis-cli >/dev/null 2>&1; then
  if redis-cli -h "$TARGET_IP" -p "$TARGET_PORT" ping | grep -q PONG; then
    if [[ -n "$REDIS_KEY" ]]; then
      value="$(redis-cli -h "$TARGET_IP" -p "$TARGET_PORT" GET "$REDIS_KEY" || true)"
      if [[ -n "$REDIS_EXPECT_VALUE" && "$value" != "$REDIS_EXPECT_VALUE" ]]; then
        log "redis key value mismatch"
        exit 1
      fi
      log "redis key assertion passed"
      exit 0
    fi
    log "redis ping passed"
    exit 0
  fi
else
  printf '*1\\r\\n$4\\r\\nPING\\r\\n' | timeout 5 bash -lc "cat >/dev/tcp/${TARGET_IP}/${TARGET_PORT}" 2>/dev/null && {
    log "redis tcp probe passed; replace with redis-cli assertion before delivery"
    exit 0
  }
fi

log "redis check failed"
exit 1
"""
    )


def mysql_body(mysql_query: str, mysql_expect_text: str) -> str:
    return (
        f"MYSQL_QUERY_TEXT={shlex.quote(mysql_query)}\n"
        f"MYSQL_EXPECT_TEXT={shlex.quote(mysql_expect_text)}\n"
        """MYSQL_USER="${MYSQL_USER:-root}"
MYSQL_PASSWORD="${MYSQL_PASSWORD:-}"
MYSQL_DATABASE="${MYSQL_DATABASE:-}"

if command -v mysql >/dev/null 2>&1 && [[ -n "$MYSQL_QUERY_TEXT" ]]; then
  mysql_args=(-h "$TARGET_IP" -P "$TARGET_PORT" -u "$MYSQL_USER" --batch --skip-column-names)
  if [[ -n "$MYSQL_PASSWORD" ]]; then
    mysql_args+=("-p${MYSQL_PASSWORD}")
  fi
  if [[ -n "$MYSQL_DATABASE" ]]; then
    mysql_args+=("$MYSQL_DATABASE")
  fi
  result="$(mysql "${mysql_args[@]}" -e "$MYSQL_QUERY_TEXT" 2>/dev/null || true)"
  if [[ -n "$MYSQL_EXPECT_TEXT" && "$result" != *"$MYSQL_EXPECT_TEXT"* ]]; then
    log "mysql query result mismatch"
    exit 1
  fi
  if [[ -z "$MYSQL_EXPECT_TEXT" && -z "$result" ]]; then
    log "mysql query returned empty result"
    exit 1
  fi
  log "mysql query assertion passed"
  exit 0
fi

if command -v mysqladmin >/dev/null 2>&1; then
  if mysqladmin --connect-timeout=5 -h "$TARGET_IP" -P "$TARGET_PORT" ping >/dev/null 2>&1; then
    log "mysql ping passed"
    exit 0
  fi
else
  if timeout 5 bash -lc "cat < /dev/null > /dev/tcp/${TARGET_IP}/${TARGET_PORT}" 2>/dev/null; then
    log "mysql tcp probe passed; replace with authenticated mysqladmin assertion before delivery"
    exit 0
  fi
fi

log "mysql check failed"
exit 1
"""
    )


def ssh_body(expect_banner: str) -> str:
    return (
        f"EXPECT_BANNER={shlex.quote(expect_banner or 'SSH-')}\n"
        """banner="$(timeout 5 bash -lc "cat < /dev/tcp/${TARGET_IP}/${TARGET_PORT}" 2>/dev/null | head -n 1 || true)"
if [[ "$banner" == *"$EXPECT_BANNER"* ]]; then
  log "ssh banner observed"
  exit 0
fi

log "ssh banner not observed"
exit 1
"""
    )


def script_body(args: argparse.Namespace) -> str:
    port = default_port(args.type, args.target_port)
    body_map: Dict[str, str] = {
        "http": http_body(
            args.path,
            args.method,
            args.expect_status,
            args.expect_text,
            args.expect_header,
            args.forbid_text,
            args.forbid_header,
        ),
        "tcp": tcp_body(),
        "redis": redis_body(args.redis_key, args.redis_expect_value),
        "mysql": mysql_body(args.mysql_query, args.mysql_expect_text),
        "ssh": ssh_body(args.ssh_expect_banner),
    }
    return header(port) + body_map[args.type]


def main() -> int:
    args = parse_args()
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(script_body(args), encoding="utf-8")
    os.chmod(output, 0o755)
    result = structured_ok(
        "check_stub",
        type=args.type,
        output=str(output),
        target_port=default_port(args.type, args.target_port),
        review_required=True,
    )
    if args.format == "json":
        print(dump_json(result, pretty=True))
    else:
        print("Check stub generated")
        print(f"- type: {result['type']}")
        print(f"- output: {result['output']}")
        print("- review_required: true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
