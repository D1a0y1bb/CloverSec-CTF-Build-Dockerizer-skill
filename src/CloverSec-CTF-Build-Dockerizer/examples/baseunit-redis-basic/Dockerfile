# syntax=docker/dockerfile:1
FROM redis:7.2-alpine@sha256:5f8bafd0669a697ee564ad825c2a63e6b60b0a67c02b0089f8a250051ab6fe85


# BaseUnit generic template:
# - keep the stack minimal
# - allow version-specific service packaging
# - stay compatible with platform contracts and existing render variables
RUN set -eux; \
    if command -v apk >/dev/null 2>&1; then \
      apk add --no-cache bash ca-certificates; \
    elif command -v apt-get >/dev/null 2>&1; then \
      apt-get update && apt-get install -y --no-install-recommends bash ca-certificates && rm -rf /var/lib/apt/lists/*; \
    else \
      echo "[ERROR] 当前基础镜像不支持 apk/apt-get，无法安装 bash" >&2; \
      exit 1; \
    fi


RUN set -eux; \
    :

# 统一工作目录：start.sh 会切换到该目录
WORKDIR /data


COPY . /data
# no extra copy

ENV BASEUNIT_COMPONENT_DESCRIPTION="BaseUnit Redis sample using an official Redis image."


# defense block disabled
# ---- 平台硬约束：/start.sh /changeflag.sh 与 /flag 必须位于容器根目录 ----
COPY start.sh /start.sh
COPY changeflag.sh /changeflag.sh
COPY flag /flag

# /start.sh 与 /changeflag.sh 必须可执行；/flag 必须可读（平台启动后会写入动态 flag）
RUN chmod 555 /start.sh && chmod 555 /changeflag.sh && chmod 444 /flag
# 对外暴露端口（至少一个）
EXPOSE 6379

HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=10s CMD bash -lc 'redis-cli -h 127.0.0.1 -p 6379 ping | grep -q PONG || echo > /dev/tcp/127.0.0.1/6379'
# 默认启动入口，便于本地直接 docker run image
CMD ["/start.sh"]
