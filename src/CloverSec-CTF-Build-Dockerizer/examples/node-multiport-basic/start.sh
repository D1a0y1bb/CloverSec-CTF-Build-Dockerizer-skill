#!/bin/bash
set -euo pipefail


# Node 栈启动脚本，平台固定以 /start.sh 启动。
# 保障 /flag 存在并保持可读，便于平台后续覆盖写入
if [ ! -f /flag ]; then
  touch /flag
fi
chmod 444 /flag || true
export NODE_ENV=production


cd "/app"
: # defense block disabled

# 单服务必须 exec 主进程作为 PID1，保证信号正确传递。
START_CMD="node server.js"
if [[ -z "${START_CMD}" ]]; then
  echo "[ERROR] START_CMD 不能为空，请在 challenge.start.cmd 中设置，例如：node server.js" >&2
  exit 1
fi

echo "[INFO] exec: ${START_CMD}"
exec bash -lc "${START_CMD}"
