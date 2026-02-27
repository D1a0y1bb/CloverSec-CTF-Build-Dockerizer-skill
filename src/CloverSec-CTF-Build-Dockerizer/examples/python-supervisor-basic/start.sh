#!/bin/bash
set -euo pipefail


# Python 栈启动脚本。
# 保障 /flag 存在并保持可读，便于平台后续覆盖写入
if [ ! -f /flag ]; then
  touch /flag
fi
chmod 444 /flag || true

export PYTHONUNBUFFERED=1


cd "/app"

START_CMD="supervisord -n -c /app/supervisord.conf"
if [[ -z "${START_CMD}" ]]; then
  echo "[ERROR] START_CMD 不能为空。示例：gunicorn -b 0.0.0.0:5000 app:app" >&2
  exit 1
fi

echo "[INFO] exec: ${START_CMD}"
exec bash -lc "${START_CMD}"
