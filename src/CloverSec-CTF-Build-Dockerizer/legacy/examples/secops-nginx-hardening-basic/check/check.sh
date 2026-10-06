#!/bin/bash
set -euo pipefail
TARGET_IP="${1:-${TARGET_IP:-${TARGET_HOST:-127.0.0.1}}}"
TARGET_PORT="${2:-${TARGET_PORT:-80}}"
BODY="$(curl -fsS --max-time 10 "http://${TARGET_IP}:${TARGET_PORT}/")"
if [[ "${BODY}" != *"secops-nginx-hardening-basic"* ]]; then
  echo "[FAIL] secops nginx content mismatch" >&2
  exit 1
fi
STATUS="$(curl -sS --max-time 10 -o /dev/null -w '%{http_code}' "http://${TARGET_IP}:${TARGET_PORT}/.git/config" || true)"
if [[ "${STATUS}" != "404" ]]; then
  echo "[FAIL] sensitive path should return 404, got ${STATUS}" >&2
  exit 1
fi
echo "[PASS] secops nginx healthy"
