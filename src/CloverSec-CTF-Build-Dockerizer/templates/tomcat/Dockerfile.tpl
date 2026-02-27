# syntax=docker/dockerfile:1
# Tomcat(WAR) 最小模板：适用于 ROOT.war 或 webapps 目录部署
FROM {{BASE_IMAGE}}

# 安装 bash，保障平台动态 flag 脚本执行能力。
RUN set -eux; \
    if command -v apk >/dev/null 2>&1; then \
      {{> snippets/apk-install-bash.tpl }}; \
    elif command -v apt-get >/dev/null 2>&1; then \
      {{> snippets/apt-install-bash.tpl }}; \
    else \
      echo "[ERROR] 当前基础镜像不支持 apk/apt-get，无法安装 bash" >&2; \
      exit 1; \
    fi

RUN set -eux; \
    {{RUNTIME_DEPS_INSTALL}}

{{> snippets/workdir.tpl }}

# 通常将 ROOT.war 放置到 /usr/local/tomcat/webapps/ROOT.war。
COPY {{APP_SRC}} {{APP_DST}}
{{COPY_APP}}

{{> snippets/env.tpl }}

{{> snippets/copy-flag-start.tpl }}
{{> snippets/expose.tpl }}
{{HEALTHCHECK_BLOCK}}
{{> snippets/cmd-start.tpl }}
