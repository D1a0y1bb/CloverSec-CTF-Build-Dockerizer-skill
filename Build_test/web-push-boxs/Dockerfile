# syntax=docker/dockerfile:1
# PHP + Apache 最小模板：适用于 PHP Web 题目
FROM docker.m.daocloud.io/library/php:7.4-cli

# Apache 分支通常是 Debian 系镜像，仍做 apk/apt 双分支兜底。
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
WORKDIR /var/www/html


# 复制代码到站点目录。
COPY src /var/www/html
# no extra copy

# no docker env


# ---- 平台硬约束：/start.sh 与 /flag 必须位于容器根目录 ----
COPY start.sh /start.sh
COPY flag /flag
# 额外拷贝一份到 Web 目录供 RCE 读取，改名为 flag_1s_h3re
COPY flag /var/www/html/flag_1s_h3re

# /start.sh 必须可执行；/flag 必须可读（平台启动后会写入动态 flag）
# 修复 Windows 下生成的脚本可能带有的 CRLF 问题
RUN sed -i 's/\r$//' /start.sh && chmod 555 /start.sh && chmod 444 /flag && chmod 444 /var/www/html/flag_1s_h3re

# 对外暴露端口（至少一个）
EXPOSE 5000

# 默认启动入口，便于本地直接 docker run image
CMD ["/start.sh"]
