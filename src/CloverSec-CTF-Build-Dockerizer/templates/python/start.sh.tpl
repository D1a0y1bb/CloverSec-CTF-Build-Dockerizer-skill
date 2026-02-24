{{> snippets/start-header.tpl }}

# Python 栈启动脚本。
{{> snippets/ensure-flag.tpl }}
{{> snippets/env.tpl }}

cd "{{WORKDIR}}"

START_CMD="{{START_CMD}}"
if [[ -z "${START_CMD}" ]]; then
  echo "[ERROR] START_CMD 不能为空。示例：gunicorn -b 0.0.0.0:5000 app:app" >&2
  exit 1
fi

echo "[INFO] exec: ${START_CMD}"
exec bash -lc "${START_CMD}"
