#!/bin/bash
set -euo pipefail


# PHP(Apache) 栈启动脚本。
# 保障 /flag 存在并保持可读，便于平台后续覆盖写入
if [ ! -f /flag ]; then
  touch /flag
fi
chmod 444 /flag || true
:


cd "/var/www/html"
: # defense block disabled

START_CMD="apache2-foreground"
if [[ -z "${START_CMD}" ]]; then
  START_CMD="apache2-foreground"
fi

echo "[INFO] exec: ${START_CMD}"
exec bash -lc "${START_CMD}"
