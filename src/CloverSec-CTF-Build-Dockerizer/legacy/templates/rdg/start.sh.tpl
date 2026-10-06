{{> snippets/start-header.tpl }}

# RDG 栈启动脚本：先起 sshd/ttyd 旁路，再以前台 exec 拉起主服务。
{{RDG_FLAG_START_BLOCK}}
{{> snippets/env.tpl }}

cd "{{WORKDIR}}"

if [[ "{{RDG_ENABLE_SSHD}}" == "true" ]]; then
  if command -v sshd >/dev/null 2>&1; then
    /usr/sbin/sshd -D -e -p "{{RDG_SSHD_PORT}}" >/tmp/rdg-sshd.log 2>&1 &
    echo "[INFO] RDG sshd started on :{{RDG_SSHD_PORT}}"
  else
    echo "[ERROR] RDG enable_sshd=true 但镜像中未检测到 sshd" >&2
    exit 1
  fi
fi

if [[ "{{RDG_ENABLE_TTYD}}" == "true" ]]; then
  if [[ -x /ttyd ]]; then
    TTYD_PORT="{{RDG_TTYD_PORT}}"
    TTYD_LOGIN_CMD="{{RDG_TTYD_LOGIN_CMD}}"
    CTF_USER="{{RDG_CTF_USER}}"
    CTF_PASS="{{RDG_CTF_PASSWORD}}"
    AUTH_MODE="{{RDG_SSHD_PASSWORD_AUTH_TEXT}}"
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

if [[ "{{RDG_CHECK_ENABLED}}" == "true" && "{{RDG_SCORING_MODE}}" == "check_service" ]]; then
  echo "[INFO] RDG scoring mode: check_service (script: {{RDG_CHECK_SCRIPT_PATH}})"
fi

START_CMD="{{START_CMD}}"
if [[ -z "${START_CMD}" ]]; then
  echo "[ERROR] START_CMD 不能为空。请在 challenge.start.cmd 中显式指定主服务命令。" >&2
  exit 1
fi

echo "[INFO] exec: ${START_CMD}"
exec bash -lc "${START_CMD}"
