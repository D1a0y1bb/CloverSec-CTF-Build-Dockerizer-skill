# syntax=docker/dockerfile:1
# LAMP 最小模板：Apache + PHP + MariaDB（同容器多服务）
FROM {{BASE_IMAGE}}

# 安装 bash 与核心服务；清理 apt 缓存控制镜像体积。
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      bash ca-certificates \
      apache2 php libapache2-mod-php \
      mariadb-server \
 && rm -rf /var/lib/apt/lists/*

RUN set -eux; \
    {{RUNTIME_DEPS_INSTALL}}

{{> snippets/workdir.tpl }}

COPY {{APP_SRC}} {{APP_DST}}
{{COPY_APP}}

{{> snippets/env.tpl }}

{{> snippets/copy-flag-start.tpl }}
{{> snippets/expose.tpl }}
{{> snippets/cmd-start.tpl }}
