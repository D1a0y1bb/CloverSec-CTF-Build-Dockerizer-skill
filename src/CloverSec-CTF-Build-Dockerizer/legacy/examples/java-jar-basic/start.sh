#!/bin/bash
set -euo pipefail

cd "/app"

START_CMD="java -jar app.jar"
if [[ -z "${START_CMD}" ]]; then
  echo "[ERROR] START_CMD 不能为空。示例：java -jar app.jar" >&2
  exit 1
fi

echo "[INFO] exec: ${START_CMD}"
exec bash -lc "${START_CMD}"
