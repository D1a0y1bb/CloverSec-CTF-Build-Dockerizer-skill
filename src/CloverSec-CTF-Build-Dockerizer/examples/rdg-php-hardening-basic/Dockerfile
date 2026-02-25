# syntax=docker/dockerfile:1
# RDG 最小模板：兼容题目服务 + ttyd 旁路（存在即启用）
FROM php:8.2-apache

# 平台契约依赖 bash；RDG 常见调试链路依赖 curl/sudo/procps。
RUN set -eux; \
    if command -v apk >/dev/null 2>&1; then \
      apk add --no-cache bash ca-certificates curl sudo shadow procps; \
    elif command -v apt-get >/dev/null 2>&1; then \
      apt-get update && apt-get install -y --no-install-recommends bash ca-certificates curl sudo procps && rm -rf /var/lib/apt/lists/*; \
    else \
      echo "[ERROR] 当前基础镜像不支持 apk/apt-get，无法安装 RDG 依赖" >&2; \
      exit 1; \
    fi

# 可选运行时依赖安装。
RUN set -eux; \
    :

# RDG 建议创建 ctf 用户（best-effort，不强阻断）。
RUN set -eux; \
    if ! id ctf >/dev/null 2>&1; then \
      if command -v useradd >/dev/null 2>&1; then \
        useradd -m -s /bin/bash ctf; \
      elif command -v adduser >/dev/null 2>&1; then \
        adduser -D -s /bin/bash ctf; \
      fi; \
    fi

# 统一工作目录：start.sh 会切换到该目录
WORKDIR /app


# 复制题目业务文件。
COPY . /app
# no extra copy

# no docker env


# 平台硬约束文件。
# ---- 平台硬约束：/start.sh 与 /flag 必须位于容器根目录 ----
COPY start.sh /start.sh
COPY flag /flag

# /start.sh 必须可执行；/flag 必须可读（平台启动后会写入动态 flag）
RUN chmod 555 /start.sh && chmod 444 /flag

# 对外暴露端口（至少一个）
EXPOSE 80

# 默认启动入口，便于本地直接 docker run image
CMD ["/start.sh"]
