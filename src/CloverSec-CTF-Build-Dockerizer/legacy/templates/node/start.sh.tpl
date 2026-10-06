{{> snippets/start-header.tpl }}

# Node 栈启动脚本，平台固定以 /start.sh 启动。
{{RDG_FLAG_START_BLOCK}}
{{> snippets/env.tpl }}

cd "{{WORKDIR}}"
{{DEFENSE_START_BLOCK}}

# 单服务必须 exec 主进程作为 PID1，保证信号正确传递。
START_CMD="{{START_CMD}}"
if [[ -z "${START_CMD}" ]]; then
  echo "[ERROR] START_CMD 不能为空，请在 challenge.start.cmd 中设置，例如：node server.js" >&2
  exit 1
fi

echo "[INFO] exec: ${START_CMD}"
exec bash -lc "${START_CMD}"
