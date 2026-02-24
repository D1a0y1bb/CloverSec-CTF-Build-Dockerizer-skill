# syntax=docker/dockerfile:1
# Pwn 最小模板：默认按 xinetd 前台模式部署 Jeopardy 题目
FROM debian:bookworm-slim

# 平台动态 flag 注入依赖 /bin/bash，且 Pwn 场景需要 xinetd 提供网络服务。
RUN apt-get update \
 && apt-get install -y --no-install-recommends bash ca-certificates xinetd \
 && rm -rf /var/lib/apt/lists/*

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


# 与平台启动方式保持一致。
# 默认启动入口，便于本地直接 docker run image
CMD ["/start.sh"]
