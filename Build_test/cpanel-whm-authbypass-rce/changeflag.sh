#!/bin/bash
set -euo pipefail

TARGET_PATH="${FLAG_PATH:-/flag}"
DEFAULT_FLAG="flag{07c0287d8f278451f9b19d59ea89e2f6}"
if [[ -n "${FLAG:-}" ]]; then
  TARGET_FLAG="${FLAG}"
elif [[ -n "${CTF_FLAG:-}" ]]; then
  TARGET_FLAG="${CTF_FLAG}"
elif [[ $# -gt 0 && -n "${1:-}" ]]; then
  TARGET_FLAG="$1"
else
  TARGET_FLAG="${DEFAULT_FLAG}"
fi

mkdir -p "$(dirname "${TARGET_PATH}")"
printf '%s\n' "${TARGET_FLAG}" > "${TARGET_PATH}"
chmod 444 "${TARGET_PATH}"
chown root:root "${TARGET_PATH}" 2>/dev/null || true

echo "[INFO] flag updated"
