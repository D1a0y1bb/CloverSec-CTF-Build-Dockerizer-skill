{{> snippets/start-header.tpl }}

# PHP(Apache) 栈启动脚本。
{{> snippets/ensure-flag.tpl }}
{{> snippets/env.tpl }}

cd "{{WORKDIR}}"

START_CMD="{{START_CMD}}"
if [[ -z "${START_CMD}" ]]; then
  START_CMD="apache2-foreground"
fi

echo "[INFO] exec: ${START_CMD}"
exec bash -lc "${START_CMD}"
