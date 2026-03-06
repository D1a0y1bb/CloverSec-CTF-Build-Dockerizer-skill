#!/bin/bash
set -euo pipefail


# SecOps 栈启动脚本：先起 sshd/ttyd 旁路，再以前台 exec 拉起真实服务。
# 保障 /flag 存在并保持可读，便于平台后续覆盖写入
if [ ! -f /flag ]; then
  touch /flag
fi
chmod 444 /flag || true
:


cd "/usr/share/nginx/html"

if [[ "true" == "true" ]]; then
  if command -v sshd >/dev/null 2>&1; then
    /usr/sbin/sshd -D -e -p "22" >/tmp/secops-sshd.log 2>&1 &
    echo "[INFO] SecOps sshd started on :22"
  else
    echo "[ERROR] SecOps enable_sshd=true 但镜像中未检测到 sshd" >&2
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
        /ttyd -p "${TTYD_PORT}" -c "${CTF_USER}:${CTF_PASS}" /bin/bash -lc "${TTYD_LOGIN_CMD}" >/tmp/secops-ttyd.log 2>&1 &
      else
        /ttyd -p "${TTYD_PORT}" /bin/bash -lc "${TTYD_LOGIN_CMD}" >/tmp/secops-ttyd.log 2>&1 &
      fi
    else
      if [[ "${AUTH_MODE}" == "yes" ]]; then
        /ttyd -p "${TTYD_PORT}" -c "${CTF_USER}:${CTF_PASS}" /bin/bash >/tmp/secops-ttyd.log 2>&1 &
      else
        /ttyd -p "${TTYD_PORT}" /bin/bash >/tmp/secops-ttyd.log 2>&1 &
      fi
    fi
    echo "[INFO] SecOps ttyd started on :${TTYD_PORT}"
  else
    echo "[ERROR] SecOps enable_ttyd=true 但 /ttyd 不存在或不可执行" >&2
    exit 1
  fi
fi

if [[ "true" == "true" && "check_service" == "check_service" ]]; then
  echo "[INFO] SecOps scoring mode: check_service (script: check/check.sh)"
fi

START_CMD="nginx -g 'daemon off;'"
if [[ -z "${START_CMD}" ]]; then
  echo "[ERROR] START_CMD 不能为空。请在 challenge.start.cmd 中显式指定主服务命令。" >&2
  exit 1
fi

echo "[INFO] exec: ${START_CMD}"
exec bash -lc "${START_CMD}"
