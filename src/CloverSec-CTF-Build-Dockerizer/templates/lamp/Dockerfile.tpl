# syntax=docker/dockerfile:1
# LAMP 最小模板：Apache + PHP + MariaDB（同容器多服务）
FROM {{BASE_IMAGE}}

# 安装 bash 与核心服务，兼容 Debian/Ubuntu 与 Alpine。
RUN set -eux; \
    if command -v apk >/dev/null 2>&1; then \
      apk add --no-cache \
        bash ca-certificates \
        apache2 php php-apache2 \
        mariadb mariadb-client; \
    elif command -v apt-get >/dev/null 2>&1; then \
      apt-get update && apt-get install -y --no-install-recommends \
        bash ca-certificates \
        apache2 php libapache2-mod-php \
        mariadb-server mariadb-client \
      && rm -rf /var/lib/apt/lists/*; \
    else \
      echo "[ERROR] 当前基础镜像不支持 apk/apt-get，无法安装 LAMP 依赖" >&2; \
      exit 1; \
    fi

RUN set -eux; \
    {{RUNTIME_DEPS_INSTALL}}

{{> snippets/workdir.tpl }}

COPY {{APP_SRC}} {{APP_DST}}
{{COPY_APP}}

{{> snippets/env.tpl }}

{{> snippets/copy-flag-start.tpl }}
{{> snippets/expose.tpl }}
{{HEALTHCHECK_BLOCK}}
{{> snippets/cmd-start.tpl }}
