# syntax=docker/dockerfile:1
FROM redis:7.2-alpine@sha256:5f8bafd0669a697ee564ad825c2a63e6b60b0a67c02b0089f8a250051ab6fe85

RUN set -eux; \
    if command -v apk >/dev/null 2>&1; then \
      apk add --no-cache bash ca-certificates; \
    elif command -v apt-get >/dev/null 2>&1; then \
      apt-get update && apt-get install -y --no-install-recommends bash ca-certificates && rm -rf /var/lib/apt/lists/*; \
    else \
      echo "[ERROR] 当前基础镜像不支持 apk/apt-get，无法安装 bash" >&2; \
      exit 1; \
    fi

WORKDIR /data

COPY . /data

ENV BASEUNIT_COMPONENT_DESCRIPTION="BaseUnit Redis sample using an official Redis image."

COPY start.sh /start.sh
RUN chmod 555 /start.sh
COPY flag /flag
RUN chmod 444 /flag
EXPOSE 6379

HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=10s CMD bash -lc 'redis-cli -h 127.0.0.1 -p 6379 ping | grep -q PONG || echo > /dev/tcp/127.0.0.1/6379'
CMD ["/start.sh"]
