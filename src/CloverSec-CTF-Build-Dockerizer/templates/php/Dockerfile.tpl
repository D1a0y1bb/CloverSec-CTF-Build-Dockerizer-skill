# syntax=docker/dockerfile:1
# PHP + Apache 最小模板：适用于 PHP Web 题目
FROM {{BASE_IMAGE}}

# Apache 分支通常是 Debian 系镜像，仍做 apk/apt 双分支兜底。
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

# 复制代码到站点目录。
COPY {{APP_SRC}} {{APP_DST}}
{{COPY_APP}}

{{> snippets/env.tpl }}

{{> snippets/copy-flag-start.tpl }}
{{> snippets/expose.tpl }}
{{> snippets/cmd-start.tpl }}
