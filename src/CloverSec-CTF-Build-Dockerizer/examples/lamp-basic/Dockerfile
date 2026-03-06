# syntax=docker/dockerfile:1
FROM debian:bookworm-slim


# LAMP 最小模板：Apache + PHP + MariaDB（同容器多服务）
# 安装 bash 与核心服务，兼容 Debian/Ubuntu 与 Alpine。
RUN set -eux; \
    if command -v apk >/dev/null 2>&1; then \
      apk add --no-cache \
        bash ca-certificates \
        apache2 php php-apache2 \
        mariadb mariadb-client; \
    elif command -v apt-get >/dev/null 2>&1; then \
      apt-get update && apt-get install -y --no-install-recommends \
        bash ca-certificates \
        apache2 php libapache2-mod-php \
        mariadb-server mariadb-client \
      && rm -rf /var/lib/apt/lists/*; \
    else \
      echo "[ERROR] 当前基础镜像不支持 apk/apt-get，无法安装 LAMP 依赖" >&2; \
      exit 1; \
    fi

RUN set -eux; \
    :

# 统一工作目录：start.sh 会切换到该目录
WORKDIR /var/www/html


COPY . /var/www/html
# no extra copy

# no docker env


# defense block disabled

# defense block disabled
# ---- 平台硬约束：/start.sh /changeflag.sh 与 /flag 必须位于容器根目录 ----
COPY start.sh /start.sh
COPY changeflag.sh /changeflag.sh
COPY flag /flag

# /start.sh 与 /changeflag.sh 必须可执行；/flag 必须可读（平台启动后会写入动态 flag）
RUN chmod 555 /start.sh && chmod 555 /changeflag.sh && chmod 444 /flag
# 对外暴露端口（至少一个）
EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=10s CMD bash -lc 'echo > /dev/tcp/127.0.0.1/80'
# 默认启动入口，便于本地直接 docker run image
CMD ["/start.sh"]
