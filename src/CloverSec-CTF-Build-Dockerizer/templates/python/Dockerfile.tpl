{{> snippets/docker-common-prolog.tpl }}

# Python 最小模板：适用于 Flask/FastAPI/自定义 HTTP 服务
{{> snippets/run-bash-bootstrap.tpl }}

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

{{> snippets/docker-common-epilog.tpl }}
