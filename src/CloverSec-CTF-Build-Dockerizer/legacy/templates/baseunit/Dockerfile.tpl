{{> snippets/docker-common-prolog.tpl }}

# BaseUnit generic template:
# - keep the stack minimal
# - allow version-specific service packaging
# - stay compatible with platform contracts and existing render variables
{{> snippets/run-bash-bootstrap.tpl }}

RUN set -eux; \
    {{RUNTIME_DEPS_INSTALL}}

{{> snippets/workdir.tpl }}

COPY {{APP_SRC}} {{APP_DST}}
{{COPY_APP}}

{{> snippets/env.tpl }}

{{> snippets/docker-common-epilog.tpl }}
