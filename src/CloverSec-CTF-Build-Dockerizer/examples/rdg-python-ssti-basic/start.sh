#!/bin/bash
set -euo pipefail


# RDG 栈启动脚本：主服务前台 exec + ttyd 旁路（可选）。
# 保障 /flag 存在并保持可读，便于平台后续覆盖写入
if [ ! -f /flag ]; then
  touch /flag
fi
chmod 444 /flag || true

export PYTHONUNBUFFERED=1


cd "/app"

if [[ "true" == "true" ]]; then
  TTYD_BIN=""
  if command -v ttyd >/dev/null 2>&1; then
    TTYD_BIN="$(command -v ttyd)"
  elif [[ -x /ttyd ]]; then
    TTYD_BIN="/ttyd"
  elif [[ -x "/app/ttyd" ]]; then
    TTYD_BIN="/app/ttyd"
  fi

  if [[ -n "${TTYD_BIN}" ]]; then
    TTYD_PORT="8022"
    TTYD_LOGIN_CMD="/bin/bash"
    if [[ -n "${TTYD_LOGIN_CMD}" ]]; then
      "${TTYD_BIN}" -p "${TTYD_PORT}" /bin/bash -lc "${TTYD_LOGIN_CMD}" >/tmp/rdg-ttyd.log 2>&1 &
    else
      "${TTYD_BIN}" -p "${TTYD_PORT}" /bin/bash >/tmp/rdg-ttyd.log 2>&1 &
    fi
    echo "[INFO] RDG ttyd started on :${TTYD_PORT}"
  else
    echo "[WARN] RDG ttyd 未找到（缺失不阻断构建/运行）"
  fi
fi

START_CMD="python app.py"
if [[ -z "${START_CMD}" ]]; then
  echo "[ERROR] START_CMD 不能为空。请在 challenge.start.cmd 中显式指定主服务命令。" >&2
  exit 1
fi

echo "[INFO] exec: ${START_CMD}"
exec bash -lc "${START_CMD}"
