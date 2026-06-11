#!/bin/bash
set -euo pipefail

# 平台动态 flag 写入入口。优先使用 FLAG/CTF_FLAG 环境变量，未提供时允许将第一个参数作为兜底值。
TARGET_PATH="${FLAG_PATH:-/flag}"
DEFAULT_FLAG="flag{dynamic_flag_placeholder}"
if [[ -n "${FLAG:-}" ]]; then
  TARGET_FLAG="${FLAG}"
elif [[ -n "${CTF_FLAG:-}" ]]; then
  TARGET_FLAG="${CTF_FLAG}"
elif [[ $# -gt 0 && -n "${1:-}" ]]; then
  TARGET_FLAG="$1"
else
  TARGET_FLAG="${DEFAULT_FLAG}"
fi

if [[ -z "${TARGET_PATH}" ]]; then
  echo "[ERROR] FLAG_PATH 不能为空" >&2
  exit 2
fi

mkdir -p "$(dirname "${TARGET_PATH}")"
printf '%s\n' "${TARGET_FLAG}" > "${TARGET_PATH}"
chmod 444 "${TARGET_PATH}" || true
echo "[INFO] flag updated at ${TARGET_PATH}"
