#!/bin/bash
set -euo pipefail


# BaseUnit generic entrypoint for minimal service-pack delivery directories.
# 保障 /flag 存在并保持可读，便于平台后续覆盖写入
if [ ! -f /flag ]; then
  touch /flag
fi
chmod 444 /flag || true
export BASEUNIT_COMPONENT_DESCRIPTION='BaseUnit OpenSSH sample for operator login service images.'


cd "/app"
: # defense block disabled

START_CMD="mkdir -p /var/run/sshd /etc/ssh && ssh-keygen -A && exec /usr/sbin/sshd -D -e -p 22"
if [[ -z "${START_CMD}" ]]; then
  echo "[ERROR] START_CMD must not be empty for stack=baseunit." >&2
  exit 1
fi

echo "[INFO] exec: ${START_CMD}"
exec bash -lc "${START_CMD}"
