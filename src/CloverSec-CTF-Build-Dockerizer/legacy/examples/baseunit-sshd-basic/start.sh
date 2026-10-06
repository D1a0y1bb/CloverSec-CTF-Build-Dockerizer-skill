#!/bin/bash
set -euo pipefail

export BASEUNIT_COMPONENT_DESCRIPTION='BaseUnit OpenSSH sample for operator login service images.'

cd "/app"

START_CMD="mkdir -p /var/run/sshd /etc/ssh && ssh-keygen -A && exec /usr/sbin/sshd -D -e -p 22"
if [[ -z "${START_CMD}" ]]; then
  echo "[ERROR] START_CMD must not be empty for stack=baseunit." >&2
  exit 1
fi

echo "[INFO] exec: ${START_CMD}"
exec bash -lc "${START_CMD}"
