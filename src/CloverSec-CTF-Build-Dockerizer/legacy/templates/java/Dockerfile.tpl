{{> snippets/docker-common-prolog.tpl }}

# Java JAR 最小模板：适用于目录中已包含可运行 app.jar
{{> snippets/run-bash-bootstrap.tpl }}

RUN set -eux; \
    {{RUNTIME_DEPS_INSTALL}}

{{> snippets/workdir.tpl }}

COPY {{APP_SRC}} {{APP_DST}}
{{COPY_APP}}

{{> snippets/env.tpl }}

{{DEFENSE_DOCKER_BLOCK}}

{{> snippets/docker-common-epilog.tpl }}
