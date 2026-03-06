{{> snippets/docker-common-prolog.tpl }}

# Tomcat(WAR) 最小模板：适用于 ROOT.war 或 webapps 目录部署
{{> snippets/run-bash-bootstrap.tpl }}

RUN set -eux; \
    {{RUNTIME_DEPS_INSTALL}}

{{> snippets/workdir.tpl }}

# 通常将 ROOT.war 放置到 /usr/local/tomcat/webapps/ROOT.war。
COPY {{APP_SRC}} {{APP_DST}}
{{COPY_APP}}

{{> snippets/env.tpl }}

{{DEFENSE_DOCKER_BLOCK}}

{{> snippets/docker-common-epilog.tpl }}
