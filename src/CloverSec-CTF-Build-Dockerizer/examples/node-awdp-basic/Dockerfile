# syntax=docker/dockerfile:1
FROM node:20-alpine


# Node.js 最小模板：适用于原生 HTTP/Express/Koa/Fastify 等 Web 题目
RUN set -eux; \
    if command -v apk >/dev/null 2>&1; then \
      apk add --no-cache bash ca-certificates; \
    elif command -v apt-get >/dev/null 2>&1; then \
      apt-get update && apt-get install -y --no-install-recommends bash ca-certificates && rm -rf /var/lib/apt/lists/*; \
    else \
      echo "[ERROR] 当前基础镜像不支持 apk/apt-get，无法安装 bash" >&2; \
      exit 1; \
    fi


# 可选运行时依赖（无额外依赖时渲染为 :）。
RUN set -eux; \
    :

# 工作目录统一由模板变量控制，便于 start.sh 与 Dockerfile 对齐。
# 统一工作目录：start.sh 会切换到该目录
WORKDIR /app


# 复制题目代码。
COPY . /app
# no extra copy

# 可选环境变量（为空时会渲染为注释或空操作）。
ENV NODE_ENV="production"


# 依赖安装块由渲染器生成：有 lock 优先 npm ci，无 lock 回退 npm install。
RUN set -eux; \
    if [ -f package-lock.json ] || [ -f npm-shrinkwrap.json ]; then \
      npm ci --omit=dev || npm ci; \
      npm cache clean --force || true; \
    elif [ -f package.json ]; then \
      npm install --omit=dev || npm install; \
      npm cache clean --force || true; \
    else \
      echo "[INFO] 未检测到 package.json，跳过 npm 安装"; \
    fi

# ---- V2 defense block：用于非 RDG/非 SecOps 栈按 profile 注入运维旁路 ----
RUN set -eux; \
    if [ "true" = "true" ]; then \
      if command -v apk >/dev/null 2>&1; then \
        apk add --no-cache bash ca-certificates curl sudo shadow procps openssh; \
      elif command -v apt-get >/dev/null 2>&1; then \
        apt-get update && apt-get install -y --no-install-recommends bash ca-certificates curl sudo procps openssh-server && rm -rf /var/lib/apt/lists/*; \
      else \
        echo "[ERROR] 当前基础镜像不支持 apk/apt-get，无法安装 defense 依赖" >&2; \
        exit 1; \
      fi; \
      CTF_USER="ctf"; \
      CTF_PASS="123456"; \
      if ! id "${CTF_USER}" >/dev/null 2>&1; then \
        if command -v useradd >/dev/null 2>&1; then \
          useradd -m -s /bin/bash "${CTF_USER}"; \
        elif command -v adduser >/dev/null 2>&1; then \
          adduser -D -s /bin/bash "${CTF_USER}"; \
        fi; \
      fi; \
      echo "${CTF_USER}:${CTF_PASS}" | chpasswd; \
      if [ "false" = "true" ]; then \
        if command -v usermod >/dev/null 2>&1; then \
          usermod -aG root "${CTF_USER}" || true; \
        fi; \
        if command -v addgroup >/dev/null 2>&1; then \
          addgroup "${CTF_USER}" root || true; \
        fi; \
      fi; \
      if [ "true" = "true" ]; then \
        TTYD_SRC="/app/ttyd"; \
        if [ -f "${TTYD_SRC}" ]; then \
          cp "${TTYD_SRC}" /ttyd; \
      elif [ "true" = "true" ]; then \
        if command -v apk >/dev/null 2>&1; then \
          apk add --no-cache ttyd || true; \
        elif command -v apt-get >/dev/null 2>&1; then \
          (apt-get update && apt-get install -y --no-install-recommends ttyd && rm -rf /var/lib/apt/lists/*) || true; \
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
          echo "[ERROR] defense 要求 /ttyd。未在题目目录命中且安装回退失败。" >&2; \
          exit 1; \
        fi; \
        chmod 755 /ttyd; \
      fi; \
      if [ "true" = "true" ]; then \
        mkdir -p /var/run/sshd /etc/ssh; \
        ssh-keygen -A; \
        printf '%s\n' \
          "Port 22" \
          "Protocol 2" \
          "PermitRootLogin no" \
          "PasswordAuthentication yes" \
          "ChallengeResponseAuthentication no" \
          "UsePAM no" \
          "X11Forwarding no" \
          "AllowUsers ctf" \
          "PidFile /var/run/sshd.pid" \
        > /etc/ssh/sshd_config; \
      fi; \
    else \
      :; \
    fi

# ---- V2 defense block：用于非 RDG/非 SecOps 栈按 profile 注入运维旁路 ----
RUN set -eux; \
    if [ "true" = "true" ]; then \
      if command -v apk >/dev/null 2>&1; then \
        apk add --no-cache bash ca-certificates curl sudo shadow procps openssh; \
      elif command -v apt-get >/dev/null 2>&1; then \
        apt-get update && apt-get install -y --no-install-recommends bash ca-certificates curl sudo procps openssh-server && rm -rf /var/lib/apt/lists/*; \
      else \
        echo "[ERROR] 当前基础镜像不支持 apk/apt-get，无法安装 defense 依赖" >&2; \
        exit 1; \
      fi; \
      CTF_USER="ctf"; \
      CTF_PASS="123456"; \
      if ! id "${CTF_USER}" >/dev/null 2>&1; then \
        if command -v useradd >/dev/null 2>&1; then \
          useradd -m -s /bin/bash "${CTF_USER}"; \
        elif command -v adduser >/dev/null 2>&1; then \
          adduser -D -s /bin/bash "${CTF_USER}"; \
        fi; \
      fi; \
      echo "${CTF_USER}:${CTF_PASS}" | chpasswd; \
      if [ "false" = "true" ]; then \
        if command -v usermod >/dev/null 2>&1; then \
          usermod -aG root "${CTF_USER}" || true; \
        fi; \
        if command -v addgroup >/dev/null 2>&1; then \
          addgroup "${CTF_USER}" root || true; \
        fi; \
      fi; \
      if [ "true" = "true" ]; then \
        TTYD_SRC="/app/ttyd"; \
        if [ -f "${TTYD_SRC}" ]; then \
          cp "${TTYD_SRC}" /ttyd; \
      elif [ "true" = "true" ]; then \
        if command -v apk >/dev/null 2>&1; then \
          apk add --no-cache ttyd || true; \
        elif command -v apt-get >/dev/null 2>&1; then \
          (apt-get update && apt-get install -y --no-install-recommends ttyd && rm -rf /var/lib/apt/lists/*) || true; \
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
          echo "[ERROR] defense 要求 /ttyd。未在题目目录命中且安装回退失败。" >&2; \
          exit 1; \
        fi; \
        chmod 755 /ttyd; \
      fi; \
      if [ "true" = "true" ]; then \
        mkdir -p /var/run/sshd /etc/ssh; \
        ssh-keygen -A; \
        printf '%s\n' \
          "Port 22" \
          "Protocol 2" \
          "PermitRootLogin no" \
          "PasswordAuthentication yes" \
          "ChallengeResponseAuthentication no" \
          "UsePAM no" \
          "X11Forwarding no" \
          "AllowUsers ctf" \
          "PidFile /var/run/sshd.pid" \
        > /etc/ssh/sshd_config; \
      fi; \
    else \
      :; \
    fi
# ---- 平台硬约束：/start.sh /changeflag.sh 与 /flag 必须位于容器根目录 ----
COPY start.sh /start.sh
COPY changeflag.sh /changeflag.sh
COPY flag /flag

# /start.sh 与 /changeflag.sh 必须可执行；/flag 必须可读（平台启动后会写入动态 flag）
RUN chmod 555 /start.sh && chmod 555 /changeflag.sh && chmod 444 /flag
# 对外暴露端口（至少一个）
EXPOSE 3000 22 8022

HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=10s CMD bash -lc 'echo > /dev/tcp/127.0.0.1/3000'
# 默认启动入口，便于本地直接 docker run image
CMD ["/start.sh"]
