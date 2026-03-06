{{> snippets/start-header.tpl }}

# Tomcat 栈启动脚本。
{{RDG_FLAG_START_BLOCK}}
{{> snippets/env.tpl }}

cd "{{WORKDIR}}"
{{DEFENSE_START_BLOCK}}

START_CMD="{{START_CMD}}"
if [[ -z "${START_CMD}" ]]; then
  START_CMD="catalina.sh run"
fi

echo "[INFO] exec: ${START_CMD}"
exec bash -lc "${START_CMD}"
