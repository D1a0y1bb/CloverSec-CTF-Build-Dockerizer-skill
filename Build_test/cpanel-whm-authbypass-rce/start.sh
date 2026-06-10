#!/bin/bash
set -euo pipefail

cd /opt/whm

if [[ -n "${FLAG:-${CTF_FLAG:-}}" ]]; then
  /changeflag.sh "${FLAG:-${CTF_FLAG:-}}"
fi

echo "[INFO] host management service is ready on :2087"
echo "[INFO] Session files: /var/cpanel/sessions/raw"

exec python3 /opt/whm/whm_mock.py
