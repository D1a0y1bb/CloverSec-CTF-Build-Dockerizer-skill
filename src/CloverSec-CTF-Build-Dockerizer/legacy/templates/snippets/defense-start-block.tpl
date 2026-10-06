if [[ "{{DEFENSE_ENABLED}}" == "true" ]]; then
  if [[ "{{RDG_ENABLE_SSHD}}" == "true" ]]; then
    if command -v sshd >/dev/null 2>&1; then
      /usr/sbin/sshd -D -e -p "{{RDG_SSHD_PORT}}" >/tmp/defense-sshd.log 2>&1 &
      echo "[INFO] defense sshd started on :{{RDG_SSHD_PORT}}"
    else
      echo "[ERROR] defense enable_sshd=true 但镜像中未检测到 sshd" >&2
      exit 1
    fi
  fi

  if [[ "{{RDG_ENABLE_TTYD}}" == "true" ]]; then
    if [[ -x /ttyd ]]; then
      TTYD_PORT="{{RDG_TTYD_PORT}}"
      TTYD_LOGIN_CMD="cd {{WORKDIR}} && {{RDG_TTYD_LOGIN_CMD}}"
      CTF_USER="{{RDG_CTF_USER}}"
      CTF_PASS="{{RDG_CTF_PASSWORD}}"
      AUTH_MODE="{{RDG_SSHD_PASSWORD_AUTH_TEXT}}"
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
