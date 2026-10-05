#!/bin/bash
set -euo pipefail

cd "/usr/local/tomcat"

START_CMD="catalina.sh run"
if [[ -z "${START_CMD}" ]]; then
  START_CMD="catalina.sh run"
fi

echo "[INFO] exec: ${START_CMD}"
exec bash -lc "${START_CMD}"
