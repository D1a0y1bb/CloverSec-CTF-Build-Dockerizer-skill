#!/bin/bash
set -euo pipefail

export NODE_ENV=production

cd "/app"
if [[ "true" == "true" ]]; then
  if [[ "true" == "true" ]]; then
    if command -v sshd >/dev/null 2>&1; then
      /usr/sbin/sshd -D -e -p "22" >/tmp/defense-sshd.log 2>&1 &
      echo "[INFO] defense sshd started on :22"
    else
      echo "[ERROR] defense enable_sshd=true 但镜像中未检测到 sshd" >&2
      exit 1
    fi
  fi

  if [[ "true" == "true" ]]; then
    if [[ -x /ttyd ]]; then
      TTYD_PORT="8022"
      TTYD_LOGIN_CMD="cd /app && /bin/bash"
      CTF_USER="ctf"
      CTF_PASS="123456"
      AUTH_MODE="yes"
      if [[ "${AUTH_MODE}" == "yes" ]]; then
        /ttyd -p "${TTYD_PORT}" -c "${CTF_USER}:${CTF_PASS}" /bin/bash -lc "${TTYD_LOGIN_CMD}" >/tmp/defense-ttyd.log 2>&1 &
      else
        /ttyd -p "${TTYD_PORT}" /bin/bash -lc "${TTYD_LOGIN_CMD}" >/tmp/defense-ttyd.log 2>&1 &
      fi
      echo "[INFO] defense ttyd started on :${TTYD_PORT}"
    else
      echo "[ERROR] defense enable_ttyd=true 但 /ttyd 不存在或不可执行" >&2
      exit 1
    fi
  fi
fi

START_CMD="node server.js"
if [[ -z "${START_CMD}" ]]; then
  echo "[ERROR] START_CMD 不能为空，请在 challenge.start.cmd 中设置，例如：node server.js" >&2
  exit 1
fi

echo "[INFO] exec: ${START_CMD}"
exec bash -lc "${START_CMD}"
