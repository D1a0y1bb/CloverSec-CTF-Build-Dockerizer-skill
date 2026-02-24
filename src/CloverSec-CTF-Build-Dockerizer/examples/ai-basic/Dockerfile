# syntax=docker/dockerfile:1
# AI 最小模板：默认 CPU 推理服务，优先 gunicorn 前台运行
FROM python:3.11-slim

# 平台动态 flag 注入要求 /bin/bash，需兼容 apt/apk 两类基础镜像。
RUN set -eux; \
    if command -v apk >/dev/null 2>&1; then \
      apk add --no-cache bash ca-certificates; \
    elif command -v apt-get >/dev/null 2>&1; then \
      apt-get update && apt-get install -y --no-install-recommends bash ca-certificates && rm -rf /var/lib/apt/lists/*; \
    else \
      echo "[ERROR] 当前基础镜像不支持 apk/apt-get，无法安装 bash" >&2; \
      exit 1; \
    fi

# 可选运行时依赖安装。
RUN set -eux; \
    :

# 工作目录统一由模板变量控制。
# 统一工作目录：start.sh 会切换到该目录
WORKDIR /app


# 复制应用代码。
COPY . /app
# no extra copy

# 默认收紧数值计算线程，规避高核心宿主机线程创建失败。
ENV OPENBLAS_NUM_THREADS=1 \
    OMP_NUM_THREADS=1 \
    NUMEXPR_NUM_THREADS=1 \
    GOTO_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    MALLOC_ARENA_MAX=2 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 可选额外环境变量。
ENV OPENBLAS_NUM_THREADS="1"
ENV OMP_NUM_THREADS="1"


# Python 依赖安装必须使用 --no-cache-dir 以控制镜像体积。
RUN set -eux; \
    if [ -f requirements.txt ]; then \
      pip install --no-cache-dir -r requirements.txt; \
    else \
      echo "[INFO] 未检测到 requirements.txt，跳过 pip 安装"; \
    fi

# 平台硬约束文件。
# ---- 平台硬约束：/start.sh 与 /flag 必须位于容器根目录 ----
COPY start.sh /start.sh
COPY flag /flag

# /start.sh 必须可执行；/flag 必须可读（平台启动后会写入动态 flag）
RUN chmod 555 /start.sh && chmod 444 /flag


# 暴露服务端口（默认 5000）。
# 对外暴露端口（至少一个）
EXPOSE 5000


# 保持与平台一致的默认入口。
# 默认启动入口，便于本地直接 docker run image
CMD ["/start.sh"]
