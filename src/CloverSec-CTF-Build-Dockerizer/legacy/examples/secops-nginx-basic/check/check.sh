#!/bin/bash
set -euo pipefail

TARGET_IP="${1:-${TARGET_IP:-${TARGET_HOST:-127.0.0.1}}}"
TARGET_PORT="${2:-${TARGET_PORT:-80}}"
TARGET_URL="http://${TARGET_IP}:${TARGET_PORT}/"

body="$(curl -fsS --max-time 5 "${TARGET_URL}")"
header="$(curl -fsSI --max-time 5 "${TARGET_URL}" | tr -d '\r')"

if [[ "${body}" != *"secops-nginx-basic"* ]]; then
  echo "[CHECK] homepage body mismatch" >&2
  exit 1
fi

if [[ "${header}" != *"X-SecOps-Mode: nginx-hardening"* ]]; then
  echo "[CHECK] missing hardened response header" >&2
  exit 1
fi

echo "[CHECK] secops-nginx-basic passed"
exit 0
