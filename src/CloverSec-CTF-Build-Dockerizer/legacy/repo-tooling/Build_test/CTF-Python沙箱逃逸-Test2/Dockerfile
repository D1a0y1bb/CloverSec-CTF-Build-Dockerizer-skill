# syntax=docker/dockerfile:1
# Python 最小模板：适用于 Flask/FastAPI/自定义 HTTP 服务
FROM python:3.9-slim

# 安装 bash，确保平台 /bin/bash /changeflag.sh 可执行。
RUN set -eux; \
    if command -v apk >/dev/null 2>&1; then \
      apk add --no-cache bash ca-certificates; \
    elif command -v apt-get >/dev/null 2>&1; then \
      apt-get update && apt-get install -y --no-install-recommends bash ca-certificates gcc libc6-dev && rm -rf /var/lib/apt/lists/*; \
    else \
      echo "[ERROR] 当前基础镜像不支持 apk/apt-get，无法安装 bash" >&2; \
      exit 1; \
    fi

RUN set -eux; \
    :

# 统一工作目录：start.sh 会切换到该目录
WORKDIR /app

COPY src/requirements.txt .


# requirements 安装块由渲染器统一生成。
RUN set -eux; \
    if [ -f requirements.txt ]; then \
      pip install --no-cache-dir -r requirements.txt; \
    else \
      echo "[INFO] 未检测到 requirements.txt，跳过 pip 安装"; \
    fi

# 复制代码。
COPY src /app
# no extra copy

# no docker env


# ---- 平台硬约束：/start.sh 与 /flag 必须位于容器根目录 ----
COPY start.sh /start.sh
COPY flag /flag

# /start.sh 必须可执行；/flag 必须可读（平台启动后会写入动态 flag）
RUN chmod 555 /start.sh && chmod 400 /flag && chown root:root /flag

# Create ctf user
RUN useradd -m ctf

# Compile read_flag and set SUID
RUN gcc -o /read_flag /app/read_flag.c && chmod 4755 /read_flag


# 对外暴露端口（至少一个）
EXPOSE 5000

# 默认启动入口，便于本地直接 docker run image
CMD ["/start.sh"]
