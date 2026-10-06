#!/bin/bash
set -euo pipefail

TARGET_HOST="${1:-${TARGET_IP:-${TARGET_HOST:-127.0.0.1}}}"
TARGET_PORT="${2:-${TARGET_PORT:-2087}}"

exec 3<>"/dev/tcp/${TARGET_HOST}/${TARGET_PORT}" || exit 1
exit 0
