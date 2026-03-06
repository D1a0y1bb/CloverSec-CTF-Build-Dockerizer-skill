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

# defense block disabled

# defense block disabled
# ---- 平台硬约束：/start.sh /changeflag.sh 与 /flag 必须位于容器根目录 ----
COPY start.sh /start.sh
COPY changeflag.sh /changeflag.sh
COPY flag /flag

# /start.sh 与 /changeflag.sh 必须可执行；/flag 必须可读（平台启动后会写入动态 flag）
RUN chmod 555 /start.sh && chmod 555 /changeflag.sh && chmod 444 /flag
# 对外暴露端口（至少一个）
EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=10s CMD bash -lc 'echo > /dev/tcp/127.0.0.1/3000'
# 默认启动入口，便于本地直接 docker run image
CMD ["/start.sh"]
