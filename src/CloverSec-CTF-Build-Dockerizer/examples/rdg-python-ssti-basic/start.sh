#!/bin/bash
set -euo pipefail


# RDG 栈启动脚本：先起 sshd/ttyd 旁路，再以前台 exec 拉起主服务。
: # RDG include_flag_artifact=false：跳过 /flag 检查
export PYTHONUNBUFFERED=1


cd "/app"

if [[ "true" == "true" ]]; then
  if command -v sshd >/dev/null 2>&1; then
    /usr/sbin/sshd -D -e -p "22" >/tmp/rdg-sshd.log 2>&1 &
    echo "[INFO] RDG sshd started on :22"
  else
    echo "[ERROR] RDG enable_sshd=true 但镜像中未检测到 sshd" >&2
    exit 1
  fi
fi

if [[ "true" == "true" ]]; then
  if [[ -x /ttyd ]]; then
    TTYD_PORT="8022"
    TTYD_LOGIN_CMD="/bin/bash"
    CTF_USER="ctf"
    CTF_PASS="123456"
    AUTH_MODE="yes"
    if [[ -n "${TTYD_LOGIN_CMD}" ]]; then
      if [[ "${AUTH_MODE}" == "yes" ]]; then
        /ttyd -p "${TTYD_PORT}" -c "${CTF_USER}:${CTF_PASS}" /bin/bash -lc "${TTYD_LOGIN_CMD}" >/tmp/rdg-ttyd.log 2>&1 &
      else
        /ttyd -p "${TTYD_PORT}" /bin/bash -lc "${TTYD_LOGIN_CMD}" >/tmp/rdg-ttyd.log 2>&1 &
      fi
    else
      if [[ "${AUTH_MODE}" == "yes" ]]; then
        /ttyd -p "${TTYD_PORT}" -c "${CTF_USER}:${CTF_PASS}" /bin/bash >/tmp/rdg-ttyd.log 2>&1 &
      else
        /ttyd -p "${TTYD_PORT}" /bin/bash >/tmp/rdg-ttyd.log 2>&1 &
      fi
    fi
    echo "[INFO] RDG ttyd started on :${TTYD_PORT}"
  else
    echo "[ERROR] RDG enable_ttyd=true 但 /ttyd 不存在或不可执行" >&2
    exit 1
  fi
fi

if [[ "true" == "true" && "check_service" == "check_service" ]]; then
  echo "[INFO] RDG scoring mode: check_service (script: check/check.sh)"
fi

START_CMD="python app.py"
if [[ -z "${START_CMD}" ]]; then
  echo "[ERROR] START_CMD 不能为空。请在 challenge.start.cmd 中显式指定主服务命令。" >&2
  exit 1
fi

echo "[INFO] exec: ${START_CMD}"
exec bash -lc "${START_CMD}"
