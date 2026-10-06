#!/bin/bash
set -euo pipefail

export BASEUNIT_COMPONENT_DESCRIPTION='BaseUnit Redis sample using an official Redis image.'

cd "/data"

START_CMD="redis-server --protected-mode no --bind 0.0.0.0"
if [[ -z "${START_CMD}" ]]; then
  echo "[ERROR] START_CMD must not be empty for stack=baseunit." >&2
  exit 1
fi

echo "[INFO] exec: ${START_CMD}"
exec bash -lc "${START_CMD}"
