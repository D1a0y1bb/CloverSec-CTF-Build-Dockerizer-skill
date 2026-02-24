# syntax=docker/dockerfile:1
# LAMP 最小模板：Apache + PHP + MariaDB（同容器多服务）
FROM debian:bookworm-slim

# 安装 bash 与核心服务；清理 apt 缓存控制镜像体积。
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      bash ca-certificates \
      apache2 php libapache2-mod-php \
      mariadb-server \
 && rm -rf /var/lib/apt/lists/*

RUN set -eux; \
    :

# 统一工作目录：start.sh 会切换到该目录
WORKDIR /var/www/html


COPY . /var/www/html
# no extra copy

# no docker env


# ---- 平台硬约束：/start.sh 与 /flag 必须位于容器根目录 ----
COPY start.sh /start.sh
COPY flag /flag

# /start.sh 必须可执行；/flag 必须可读（平台启动后会写入动态 flag）
RUN chmod 555 /start.sh && chmod 444 /flag

# 对外暴露端口（至少一个）
EXPOSE 80

# 默认启动入口，便于本地直接 docker run image
CMD ["/start.sh"]
