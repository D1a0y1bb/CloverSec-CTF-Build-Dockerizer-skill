#!/bin/bash
set -euo pipefail

export NODE_ENV=production

cd "/app"

START_CMD="node server.js"
if [[ -z "${START_CMD}" ]]; then
  echo "[ERROR] START_CMD 不能为空，请在 challenge.start.cmd 中设置，例如：node server.js" >&2
  exit 1
fi

echo "[INFO] exec: ${START_CMD}"
exec bash -lc "${START_CMD}"
