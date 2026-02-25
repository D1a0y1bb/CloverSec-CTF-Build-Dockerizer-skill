#!/bin/bash
set -euo pipefail

TARGET_IP="${1:-${TARGET_IP:-${TARGET_HOST:-127.0.0.1}}}"
TARGET_PORT="${2:-${TARGET_PORT:-80}}"
BASE_URL="http://${TARGET_IP}:${TARGET_PORT}"

log() {
  printf '[CHECK][rdg-python] %s\n' "$1"
}

fail() {
  log "FAIL: $1"
  exit 1
}

fetch_url() {
  local url="$1"
  local max_retry="${2:-8}"
  local attempt=1
  while (( attempt <= max_retry )); do
    if curl -fsS --max-time 10 "${url}"; then
      return 0
    fi
    sleep 1
    attempt=$((attempt + 1))
  done
  return 1
}

if [[ -z "${TARGET_IP}" || -z "${TARGET_PORT}" ]]; then
  log "usage: bash check/check.sh [target_ip] [target_port]"
  exit 2
fi

check_index_health() {
  local resp
  if ! resp="$(fetch_url "${BASE_URL}/")"; then
    fail "index request failed"
  fi

  if [[ "${resp}" != *"RDG Python sample is running."* ]]; then
    fail "index content mismatch"
  fi

  log "PASS: index health check"
}

check_ssti_exploit_blocked() {
  local payload
  local resp

  payload='%7B%7B7*7%7D%7D'
  if ! resp="$(fetch_url "${BASE_URL}/?id=${payload}")"; then
    fail "ssti probe request failed"
  fi

  if [[ "${resp}" == *">49<"* || "${resp}" == *"Hello 49"* ]]; then
    fail "negative SSTI check failed (template expression executed)"
  fi

  if [[ "${resp}" != *"{{7*7}}"* ]]; then
    fail "negative SSTI check failed (literal payload not preserved)"
  fi

  log "PASS: negative SSTI check"
}

log "target=${TARGET_IP}:${TARGET_PORT}"
check_index_health
check_ssti_exploit_blocked
log "PASS: all checks passed"
exit 0
