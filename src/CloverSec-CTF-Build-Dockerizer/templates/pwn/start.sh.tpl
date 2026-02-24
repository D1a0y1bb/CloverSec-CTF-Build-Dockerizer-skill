{{> snippets/start-header.tpl }}

# Pwn 栈启动脚本：平台固定执行 /start.sh。
# 必须启动真实服务并保持前台运行，禁止 sleep/空转保活。
{{> snippets/ensure-flag.tpl }}
{{> snippets/env.tpl }}

cd "{{WORKDIR}}"

# 兼容题目读取 /home/ctf/flag 的常见路径：保留根目录 /flag 为平台动态写入入口。
if [[ -d /home/ctf ]]; then
  cp /flag /home/ctf/flag 2>/dev/null || true
  chmod 444 /home/ctf/flag 2>/dev/null || true
fi

# 若题目目录自带 ctf.xinetd，则自动挂载到 xinetd 服务目录。
if [[ -f "{{WORKDIR}}/ctf.xinetd" ]]; then
  mkdir -p /etc/xinetd.d
  cp "{{WORKDIR}}/ctf.xinetd" /etc/xinetd.d/ctf
fi

rm -f /run/xinetd.pid

# 单服务前台策略：exec xinetd -dontfork 作为 PID1。
START_CMD="{{START_CMD}}"
if [[ -z "${START_CMD}" ]]; then
  START_CMD="/usr/sbin/xinetd -dontfork"
fi

echo "[INFO] exec: ${START_CMD}"
exec bash -lc "${START_CMD}"
