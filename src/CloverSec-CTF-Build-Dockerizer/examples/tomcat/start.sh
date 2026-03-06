#!/bin/bash
set -euo pipefail


# Tomcat 栈启动脚本。
# 保障 /flag 存在并保持可读，便于平台后续覆盖写入
if [ ! -f /flag ]; then
  touch /flag
fi
chmod 444 /flag || true
:


cd "/usr/local/tomcat"
: # defense block disabled

START_CMD="catalina.sh run"
if [[ -z "${START_CMD}" ]]; then
  START_CMD="catalina.sh run"
fi

echo "[INFO] exec: ${START_CMD}"
exec bash -lc "${START_CMD}"
