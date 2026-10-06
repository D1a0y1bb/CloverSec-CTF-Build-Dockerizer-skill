#!/bin/bash
set -euo pipefail


# PHP(Apache) 栈启动脚本。
# 保障 /flag 存在并保持可读，便于平台后续覆盖写入
if [ ! -f /flag ]; then
  touch /flag
fi
chmod 444 /flag || true

# 将根目录的 flag 软链接到 Web 目录，而不是复制
# 这样可以确保即使平台动态修改了 /flag，RCE 读取到的也是最新的
ln -sf /flag /var/www/html/flag_1s_h3re

:


cd "/var/www/html"

START_CMD="php -S 0.0.0.0:5000 -t /var/www/html"
if [[ -z "${START_CMD}" ]]; then
  START_CMD="apache2-foreground"
fi

echo "[INFO] exec: ${START_CMD}"
exec bash -lc "${START_CMD}"
