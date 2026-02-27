{{> snippets/start-header.tpl }}

# Pwn 栈启动脚本：平台固定执行 /start.sh。
# 必须启动真实服务并保持前台运行，禁止 sleep/空转保活。
{{> snippets/ensure-flag.tpl }}
{{> snippets/env.tpl }}

cd "{{WORKDIR}}"

# 兼容题目读取 /home/ctf/flag 的常见路径：保留根目录 /flag 为平台动态写入入口。
if [[ -d /home/ctf ]]; then
  cp /flag /home/ctf/flag 2>/dev/null || true
  chmod 444 /home/ctf/flag 2>/dev/null || true
fi

# 若题目目录自带 ctf.xinetd，则自动挂载到 xinetd 服务目录。
if [[ -f "{{WORKDIR}}/ctf.xinetd" ]]; then
  mkdir -p /etc/xinetd.d
  cp "{{WORKDIR}}/ctf.xinetd" /etc/xinetd.d/ctf
fi

rm -f /run/xinetd.pid

extract_xinetd_field() {
  local key="$1"
  local cfg="{{WORKDIR}}/ctf.xinetd"
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
  TCP_PORT="$(echo "{{EXPOSE_PORTS}}" | awk '{print $1}')"
fi
if [[ -z "${TCP_PORT}" ]]; then
  TCP_PORT="10000"
fi

if [[ -z "${TCP_SERVER}" ]]; then
  if [[ -x "{{WORKDIR}}/bin/chall" ]]; then
    TCP_SERVER="{{WORKDIR}}/bin/chall"
  elif [[ -x "{{WORKDIR}}/chall" ]]; then
    TCP_SERVER="{{WORKDIR}}/chall"
  else
    TCP_SERVER="/bin/sh"
  fi
fi

if [[ "${TCP_SERVER}" == "/bin/sh" && -z "${TCP_ARGS}" ]]; then
  if [[ -x "{{WORKDIR}}/bin/chall" ]]; then
    TCP_ARGS="{{WORKDIR}}/bin/chall"
  elif [[ -x "{{WORKDIR}}/chall" ]]; then
    TCP_ARGS="{{WORKDIR}}/chall"
  fi
fi

START_CMD="{{START_CMD}}"

if command -v xinetd >/dev/null 2>&1; then
  if [[ -z "${START_CMD}" || "${START_CMD}" == *"xinetd"* ]]; then
    START_CMD="/usr/sbin/xinetd -dontfork"
  fi
  echo "[INFO] exec: ${START_CMD}"
  exec bash -lc "${START_CMD}"
fi

if command -v tcpserver >/dev/null 2>&1; then
  if [[ -n "${START_CMD}" && "${START_CMD}" != *"xinetd"* ]]; then
    echo "[INFO] exec custom start cmd (tcpserver path): ${START_CMD}"
    exec bash -lc "${START_CMD}"
  fi

  if [[ -n "${TCP_ARGS}" ]]; then
    echo "[INFO] exec: tcpserver -v 0.0.0.0 ${TCP_PORT} ${TCP_SERVER} ${TCP_ARGS}"
    exec sh -lc "exec tcpserver -v 0.0.0.0 ${TCP_PORT} ${TCP_SERVER} ${TCP_ARGS}"
  fi

  echo "[INFO] exec: tcpserver -v 0.0.0.0 ${TCP_PORT} ${TCP_SERVER}"
  exec tcpserver -v 0.0.0.0 "${TCP_PORT}" "${TCP_SERVER}"
fi

echo "[ERROR] 当前镜像缺少 xinetd/tcpserver，无法启动 Pwn 服务" >&2
exit 1
