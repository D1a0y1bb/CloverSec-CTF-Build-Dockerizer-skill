#!/bin/bash
set -euo pipefail


# Java 栈启动脚本（JAR Runner）。
# 保障 /flag 存在并保持可读，便于平台后续覆盖写入
if [ ! -f /flag ]; then
  touch /flag
fi
chmod 444 /flag || true

:


cd "/app"

START_CMD="java -jar app.jar"
if [[ -z "${START_CMD}" ]]; then
  echo "[ERROR] START_CMD 不能为空。示例：java -jar app.jar" >&2
  exit 1
fi

echo "[INFO] exec: ${START_CMD}"
exec bash -lc "${START_CMD}"
