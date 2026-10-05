#!/bin/bash
set -euo pipefail

export PYTHONUNBUFFERED=1

cd "/app"

START_CMD="gunicorn -w 1 --threads 1 -b 127.0.0.1:5000 app:app"
if [[ -z "${START_CMD}" ]]; then
  echo "[ERROR] START_CMD 不能为空。示例：gunicorn -b 0.0.0.0:5000 app:app" >&2
  exit 1
fi

echo "[INFO] exec: ${START_CMD}"
exec bash -lc "${START_CMD}"
