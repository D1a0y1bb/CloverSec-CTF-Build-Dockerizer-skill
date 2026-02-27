{{> snippets/docker-common-prolog.tpl }}

# Pwn 最小模板：支持 xinetd / tcpserver / socat 前台运行
# 平台动态 flag 注入依赖 /bin/bash。
RUN set -eux; \
    if command -v apk >/dev/null 2>&1; then \
      apk add --no-cache bash ca-certificates ucspi-tcp6 socat; \
    elif command -v apt-get >/dev/null 2>&1; then \
      apt-get update && apt-get install -y --no-install-recommends bash ca-certificates xinetd socat && rm -rf /var/lib/apt/lists/*; \
    else \
      echo "[ERROR] 当前基础镜像不支持 apk/apt-get，无法安装 Pwn 依赖" >&2; \
      exit 1; \
    fi

# 可选运行时依赖，保持与渲染器统一变量契约。
RUN set -eux; \
    {{RUNTIME_DEPS_INSTALL}}

# 工作目录与 start.sh 中的 cd 必须一致，避免启动路径偏移。
{{> snippets/workdir.tpl }}

# 复制题目文件（包含二进制、xinetd 配置、附属库等）。
COPY {{APP_SRC}} {{APP_DST}}
{{COPY_APP}}

# 可选环境变量注入。
{{> snippets/env.tpl }}

{{> snippets/docker-common-epilog.tpl }}
