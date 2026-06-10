#!/bin/bash
set -euo pipefail

TARGET_FLAG="${1:-${FLAG:-${CTF_FLAG:-flag{07c0287d8f278451f9b19d59ea89e2f6}}}}"

printf '%s\n' "${TARGET_FLAG}" > /flag
chmod 444 /flag
chown root:root /flag

echo "[INFO] flag updated"
