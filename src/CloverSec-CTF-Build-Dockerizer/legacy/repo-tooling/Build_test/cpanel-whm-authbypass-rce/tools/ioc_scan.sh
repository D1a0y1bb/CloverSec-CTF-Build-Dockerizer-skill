#!/bin/bash
set -euo pipefail

SESSION_DIR="${1:-/var/cpanel/sessions/raw}"
ACCESS_LOG="${ACCESS_LOG:-/usr/local/cpanel/logs/access_log}"
found=0

echo "[INFO] scanning session files: ${SESSION_DIR}"
if [[ -d "${SESSION_DIR}" ]]; then
  while IFS= read -r -d '' file; do
    if grep -Eq '(^user=root$|^hasroot=1$|^tfa_verified=1$|^successful_internal_auth_with_timestamp=)' "${file}"; then
      echo "[SUSPICIOUS] ${file}"
      sed -n '1,80p' "${file}"
      found=1
    fi
  done < <(find "${SESSION_DIR}" -type f -print0)
else
  echo "[WARN] session directory not found"
fi

echo "[INFO] recent cpsrvd access log entries"
if [[ -f "${ACCESS_LOG}" ]]; then
  tail -n 20 "${ACCESS_LOG}"
else
  echo "[WARN] access log not found"
fi

if [[ "${found}" -eq 1 ]]; then
  echo "[INFO] suspicious session attributes were found"
else
  echo "[INFO] no suspicious session attributes found"
fi
