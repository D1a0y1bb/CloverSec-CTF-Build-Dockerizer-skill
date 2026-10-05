# syntax=docker/dockerfile:1
FROM python:3.11-slim

RUN set -eux; \
    if command -v apk >/dev/null 2>&1; then \
      apk add --no-cache bash ca-certificates; \
    elif command -v apt-get >/dev/null 2>&1; then \
      apt-get update && apt-get install -y --no-install-recommends bash ca-certificates && rm -rf /var/lib/apt/lists/*; \
    else \
      echo "[ERROR] 当前基础镜像不支持 apk/apt-get，无法安装 bash" >&2; \
      exit 1; \
    fi

WORKDIR /app

COPY . /app

RUN set -eux; \
    if [ -f requirements.txt ]; then \
      pip install --no-cache-dir -r requirements.txt; \
    else \
      echo "[INFO] 未检测到 requirements.txt，跳过 pip 安装"; \
    fi

ENV PYTHONUNBUFFERED="1"

COPY start.sh /start.sh
RUN chmod 555 /start.sh
COPY flag /flag
RUN chmod 444 /flag
EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=10s CMD bash -lc 'echo > /dev/tcp/127.0.0.1/5000'
CMD ["/start.sh"]
