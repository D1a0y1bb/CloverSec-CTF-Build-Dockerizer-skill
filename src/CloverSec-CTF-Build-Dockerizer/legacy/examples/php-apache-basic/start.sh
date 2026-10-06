#!/bin/bash
set -euo pipefail

cd "/var/www/html"

START_CMD="apache2-foreground"
if [[ -z "${START_CMD}" ]]; then
  START_CMD="apache2-foreground"
fi

echo "[INFO] exec: ${START_CMD}"
exec bash -lc "${START_CMD}"
