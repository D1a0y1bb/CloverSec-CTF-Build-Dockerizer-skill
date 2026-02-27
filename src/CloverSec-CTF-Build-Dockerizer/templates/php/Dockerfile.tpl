{{> snippets/docker-common-prolog.tpl }}

# PHP + Apache 最小模板：适用于 PHP Web 题目
# Apache 分支通常是 Debian 系镜像，仍做 apk/apt 双分支兜底。
{{> snippets/run-bash-bootstrap.tpl }}

RUN set -eux; \
    {{RUNTIME_DEPS_INSTALL}}

{{> snippets/workdir.tpl }}

# 复制代码到站点目录。
COPY {{APP_SRC}} {{APP_DST}}
{{COPY_APP}}

{{> snippets/env.tpl }}

{{> snippets/docker-common-epilog.tpl }}
