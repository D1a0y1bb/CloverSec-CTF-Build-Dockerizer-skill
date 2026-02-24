# syntax=docker/dockerfile:1
# Python 最小模板：适用于 Flask/FastAPI/自定义 HTTP 服务
FROM {{BASE_IMAGE}}

# 安装 bash，确保平台 /bin/bash /changeflag.sh 可执行。
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

# 复制代码。
COPY {{APP_SRC}} {{APP_DST}}
{{COPY_APP}}

# requirements 安装块由渲染器统一生成。
# 放在 COPY 之后，确保 requirements.txt 可见。
{{PIP_REQUIREMENTS_BLOCK}}

{{> snippets/env.tpl }}

{{> snippets/copy-flag-start.tpl }}
{{> snippets/expose.tpl }}
{{> snippets/cmd-start.tpl }}
