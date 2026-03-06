#!/bin/bash
set -euo pipefail


# BaseUnit generic entrypoint for minimal service-pack delivery directories.
# 保障 /flag 存在并保持可读，便于平台后续覆盖写入
if [ ! -f /flag ]; then
  touch /flag
fi
chmod 444 /flag || true
export BASEUNIT_COMPONENT_DESCRIPTION='BaseUnit Redis sample using an official Redis image.'


cd "/data"
: # defense block disabled

START_CMD="redis-server --protected-mode no --bind 0.0.0.0"
if [[ -z "${START_CMD}" ]]; then
  echo "[ERROR] START_CMD must not be empty for stack=baseunit." >&2
  exit 1
fi

echo "[INFO] exec: ${START_CMD}"
exec bash -lc "${START_CMD}"
