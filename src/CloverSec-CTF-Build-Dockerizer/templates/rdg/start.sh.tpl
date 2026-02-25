{{> snippets/start-header.tpl }}

# RDG 栈启动脚本：主服务前台 exec + ttyd 旁路（可选）。
{{> snippets/ensure-flag.tpl }}
{{> snippets/env.tpl }}

cd "{{WORKDIR}}"

if [[ "{{RDG_ENABLE_TTYD}}" == "true" ]]; then
  TTYD_BIN=""
  if command -v ttyd >/dev/null 2>&1; then
    TTYD_BIN="$(command -v ttyd)"
  elif [[ -x /ttyd ]]; then
    TTYD_BIN="/ttyd"
  elif [[ -x "{{WORKDIR}}/ttyd" ]]; then
    TTYD_BIN="{{WORKDIR}}/ttyd"
  fi

  if [[ -n "${TTYD_BIN}" ]]; then
    TTYD_PORT="{{RDG_TTYD_PORT}}"
    TTYD_LOGIN_CMD="{{RDG_TTYD_LOGIN_CMD}}"
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

START_CMD="{{START_CMD}}"
if [[ -z "${START_CMD}" ]]; then
  echo "[ERROR] START_CMD 不能为空。请在 challenge.start.cmd 中显式指定主服务命令。" >&2
  exit 1
fi

echo "[INFO] exec: ${START_CMD}"
exec bash -lc "${START_CMD}"
