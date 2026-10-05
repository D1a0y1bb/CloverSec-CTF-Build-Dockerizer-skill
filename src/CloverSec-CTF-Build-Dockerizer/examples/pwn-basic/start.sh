#!/bin/bash
set -euo pipefail

cd "/home/ctf"

if [[ -f "/home/ctf/ctf.xinetd" ]]; then
  mkdir -p /etc/xinetd.d
  cp "/home/ctf/ctf.xinetd" /etc/xinetd.d/ctf
fi

rm -f /run/xinetd.pid

extract_xinetd_field() {
  local key="$1"
  local cfg="/home/ctf/ctf.xinetd"
  if [[ ! -f "${cfg}" ]]; then
    return
  fi
  grep -E "^[[:space:]]*${key}[[:space:]]*=" "${cfg}" \
    | head -n1 \
    | sed -E "s/^[[:space:]]*${key}[[:space:]]*=[[:space:]]*//; s/[[:space:]]+$//"
}

TCP_PORT="$(extract_xinetd_field port || true)"
TCP_SERVER="$(extract_xinetd_field server || true)"
TCP_ARGS="$(extract_xinetd_field server_args || true)"

if [[ -z "${TCP_PORT}" ]]; then
  TCP_PORT="$(echo "10000" | awk '{print $1}')"
fi
if [[ -z "${TCP_PORT}" ]]; then
  TCP_PORT="10000"
fi

if [[ -z "${TCP_SERVER}" ]]; then
  if [[ -x "/home/ctf/bin/chall" ]]; then
    TCP_SERVER="/home/ctf/bin/chall"
  elif [[ -x "/home/ctf/chall" ]]; then
    TCP_SERVER="/home/ctf/chall"
  else
    TCP_SERVER="/bin/sh"
  fi
fi

if [[ "${TCP_SERVER}" == "/bin/sh" && -z "${TCP_ARGS}" ]]; then
  if [[ -x "/home/ctf/bin/chall" ]]; then
    TCP_ARGS="/home/ctf/bin/chall"
  elif [[ -x "/home/ctf/chall" ]]; then
    TCP_ARGS="/home/ctf/chall"
  fi
fi

START_CMD="/usr/sbin/xinetd -dontfork"
if [[ -n "${START_CMD}" ]]; then
  if [[ "${START_CMD}" == *"xinetd"* ]] && ! command -v xinetd >/dev/null 2>&1 && [[ ! -x /usr/sbin/xinetd ]]; then
    echo "[WARN] explicit start cmd requires xinetd but xinetd is unavailable; falling back to tcpserver/socat"
  else
    echo "[INFO] exec explicit start cmd: ${START_CMD}"
    exec bash -lc "${START_CMD}"
  fi
fi

if command -v xinetd >/dev/null 2>&1; then
  echo "[INFO] exec: /usr/sbin/xinetd -dontfork"
  exec /usr/sbin/xinetd -dontfork
fi

if command -v tcpserver >/dev/null 2>&1; then
  if [[ -n "${TCP_ARGS}" ]]; then
    echo "[INFO] exec: tcpserver -v 0.0.0.0 ${TCP_PORT} ${TCP_SERVER} ${TCP_ARGS}"
    exec sh -lc "exec tcpserver -v 0.0.0.0 ${TCP_PORT} ${TCP_SERVER} ${TCP_ARGS}"
  fi

  echo "[INFO] exec: tcpserver -v 0.0.0.0 ${TCP_PORT} ${TCP_SERVER}"
  exec tcpserver -v 0.0.0.0 "${TCP_PORT}" "${TCP_SERVER}"
fi

if command -v socat >/dev/null 2>&1; then
  SOCAT_CMD="${TCP_SERVER}"
  if [[ -n "${TCP_ARGS}" ]]; then
    SOCAT_CMD="${SOCAT_CMD} ${TCP_ARGS}"
  fi
  echo "[INFO] exec: socat TCP-LISTEN:${TCP_PORT},fork,reuseaddr SYSTEM:\"${SOCAT_CMD}\""
  exec sh -lc "exec socat TCP-LISTEN:${TCP_PORT},fork,reuseaddr SYSTEM:\"${SOCAT_CMD}\""
fi

echo "[ERROR] 当前镜像缺少 xinetd/tcpserver/socat，无法启动 Pwn 服务" >&2
exit 1
