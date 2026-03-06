#!/bin/bash
set -euo pipefail
TARGET_IP="${1:-${TARGET_IP:-${TARGET_HOST:-127.0.0.1}}}"
TARGET_PORT="${2:-${TARGET_PORT:-3000}}"
BODY="$(curl -fsS --max-time 10 "http://${TARGET_IP}:${TARGET_PORT}/")"
if [[ "${BODY}" != *"hello from node-awdp-basic"* ]]; then
  echo "[FAIL] node awdp content mismatch" >&2
  exit 1
fi
echo "[PASS] node awdp healthy"
