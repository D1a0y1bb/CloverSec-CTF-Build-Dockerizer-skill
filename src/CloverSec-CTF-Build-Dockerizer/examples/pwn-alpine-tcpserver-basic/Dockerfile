# syntax=docker/dockerfile:1
# Pwn 最小模板：默认按 xinetd 前台模式部署 Jeopardy 题目
FROM alpine:3.20

# 平台动态 flag 注入依赖 /bin/bash。
# Pwn 运行时兼容：Debian/Ubuntu 使用 xinetd，Alpine 使用 ucspi-tcp6(tcpserver)。
RUN set -eux; \
    if command -v apk >/dev/null 2>&1; then \
      apk add --no-cache bash ca-certificates ucspi-tcp6; \
    elif command -v apt-get >/dev/null 2>&1; then \
      apt-get update && apt-get install -y --no-install-recommends bash ca-certificates xinetd && rm -rf /var/lib/apt/lists/*; \
    else \
      echo "[ERROR] 当前基础镜像不支持 apk/apt-get，无法安装 Pwn 依赖" >&2; \
      exit 1; \
    fi

# 可选运行时依赖，保持与渲染器统一变量契约。
RUN set -eux; \
    :

# 工作目录与 start.sh 中的 cd 必须一致，避免启动路径偏移。
# 统一工作目录：start.sh 会切换到该目录
WORKDIR /home/ctf


# 复制题目文件（包含二进制、xinetd 配置、附属库等）。
COPY . /home/ctf
# no extra copy

# 可选环境变量注入。
# no docker env


# 平台硬约束：/start.sh 与 /flag 固定在容器根目录。
# ---- 平台硬约束：/start.sh 与 /flag 必须位于容器根目录 ----
COPY start.sh /start.sh
COPY flag /flag

# /start.sh 必须可执行；/flag 必须可读（平台启动后会写入动态 flag）
RUN chmod 555 /start.sh && chmod 444 /flag


# 声明服务端口（默认 10000，可在 challenge.yaml 覆盖）。
# 对外暴露端口（至少一个）
EXPOSE 10000


# 可选健康检查。
HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=10s CMD bash -lc 'echo > /dev/tcp/127.0.0.1/10000'

# 与平台启动方式保持一致。
# 默认启动入口，便于本地直接 docker run image
CMD ["/start.sh"]
