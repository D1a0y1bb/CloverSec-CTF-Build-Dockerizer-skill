#!/bin/bash
set -euo pipefail

PATCH_ROOT="$(cd "$(dirname "$0")" && pwd)"
PATCH_SRC="${PATCH_ROOT}/src"
TARGET_DIR="${PATCH_TARGET_DIR:-/app}"

if [[ ! -d "${PATCH_SRC}" ]]; then
  echo "[ERROR] patch/src 不存在" >&2
  exit 2
fi

mkdir -p "${TARGET_DIR}"
cp -a "${PATCH_SRC}/." "${TARGET_DIR}/"
echo "[INFO] patch files copied into ${TARGET_DIR}"
