{{> snippets/docker-common-prolog.tpl }}

# RDG 强化模板：ttyd + sshd 双通道，默认 check-service 判定链路。
# 平台契约与 RDG 依赖：bash/ca-certificates + sshd + 用户管理工具。
RUN set -eux; \
    if command -v apk >/dev/null 2>&1; then \
      apk add --no-cache bash ca-certificates curl sudo shadow procps openssh; \
    elif command -v apt-get >/dev/null 2>&1; then \
      apt-get update && apt-get install -y --no-install-recommends bash ca-certificates curl sudo procps openssh-server && rm -rf /var/lib/apt/lists/*; \
    else \
      echo "[ERROR] 当前基础镜像不支持 apk/apt-get，无法安装 RDG 依赖" >&2; \
      exit 1; \
    fi

# 可选运行时依赖安装。
RUN set -eux; \
    {{RUNTIME_DEPS_INSTALL}}

{{> snippets/workdir.tpl }}

# 复制题目业务文件。
COPY {{APP_SRC}} {{APP_DST}}
{{COPY_APP}}

{{> snippets/env.tpl }}

# RDG 默认用户：ctf/123456，可按题目需求加入 root 组。
RUN set -eux; \
    CTF_USER="{{RDG_CTF_USER}}"; \
    CTF_PASS="{{RDG_CTF_PASSWORD}}"; \
    if ! id "${CTF_USER}" >/dev/null 2>&1; then \
      if command -v useradd >/dev/null 2>&1; then \
        useradd -m -s /bin/bash "${CTF_USER}"; \
      elif command -v adduser >/dev/null 2>&1; then \
        adduser -D -s /bin/bash "${CTF_USER}"; \
      fi; \
    fi; \
    echo "${CTF_USER}:${CTF_PASS}" | chpasswd; \
    if [ "{{RDG_CTF_IN_ROOT_GROUP}}" = "true" ]; then \
      if command -v usermod >/dev/null 2>&1; then \
        usermod -aG root "${CTF_USER}" || true; \
      fi; \
      if command -v addgroup >/dev/null 2>&1; then \
        addgroup "${CTF_USER}" root || true; \
      fi; \
    fi

# RDG ttyd 要求：最终必须有 /ttyd（可执行）。优先题目目录，缺失时可回退安装。
RUN set -eux; \
    if [ "{{RDG_ENABLE_TTYD}}" = "true" ]; then \
      TTYD_SRC="{{WORKDIR}}/{{RDG_TTYD_BINARY_RELPATH}}"; \
      if [ -f "${TTYD_SRC}" ]; then \
        cp "${TTYD_SRC}" /ttyd; \
      elif [ "{{RDG_TTYD_INSTALL_FALLBACK}}" = "true" ]; then \
        if command -v apk >/dev/null 2>&1; then \
          apk add --no-cache ttyd || true; \
        elif command -v apt-get >/dev/null 2>&1; then \
          (apt-get update && apt-get install -y --no-install-recommends ttyd && rm -rf /var/lib/apt/lists/*) || true; \
        else \
          echo "[ERROR] 当前基础镜像不支持 ttyd 安装回退" >&2; \
          exit 1; \
        fi; \
        if ! command -v ttyd >/dev/null 2>&1; then \
          ARCH="$(uname -m)"; \
          TTYD_ARCH=""; \
          case "${ARCH}" in \
            x86_64|amd64) TTYD_ARCH="x86_64" ;; \
            aarch64|arm64) TTYD_ARCH="aarch64" ;; \
            armv7l|armv7|armhf) TTYD_ARCH="armhf" ;; \
            armv6l|arm) TTYD_ARCH="arm" ;; \
          esac; \
          if [ -n "${TTYD_ARCH}" ]; then \
            curl -fsSL "https://github.com/tsl0922/ttyd/releases/download/1.7.7/ttyd.${TTYD_ARCH}" -o /ttyd || true; \
          fi; \
        fi; \
        if command -v ttyd >/dev/null 2>&1; then \
          cp "$(command -v ttyd)" /ttyd; \
        fi; \
      fi; \
      if [ ! -f /ttyd ]; then \
        echo "[ERROR] RDG 要求 /ttyd。未在题目目录命中且安装回退失败。" >&2; \
        exit 1; \
      fi; \
      chmod 755 /ttyd; \
    fi

# RDG sshd 链路：默认端口 22，默认禁止 root 密码登录。
RUN set -eux; \
    if [ "{{RDG_ENABLE_SSHD}}" = "true" ]; then \
      mkdir -p /var/run/sshd /etc/ssh; \
      ssh-keygen -A; \
      printf '%s\n' \
        "Port {{RDG_SSHD_PORT}}" \
        "Protocol 2" \
        "PermitRootLogin no" \
        "PasswordAuthentication {{RDG_SSHD_PASSWORD_AUTH_TEXT}}" \
        "ChallengeResponseAuthentication no" \
        "UsePAM no" \
        "X11Forwarding no" \
        "AllowUsers {{RDG_CTF_USER}}" \
        "PidFile /var/run/sshd.pid" \
      > /etc/ssh/sshd_config; \
    fi

{{> snippets/docker-common-epilog.tpl }}
