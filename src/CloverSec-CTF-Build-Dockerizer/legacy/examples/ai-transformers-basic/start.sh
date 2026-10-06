#!/bin/bash
set -euo pipefail

export TRANSFORMERS_OFFLINE=1
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export GOTO_NUM_THREADS=1
export MALLOC_ARENA_MAX=2

cd "/app"

: "${OPENBLAS_NUM_THREADS:=1}"
: "${OMP_NUM_THREADS:=1}"
: "${NUMEXPR_NUM_THREADS:=1}"
: "${GOTO_NUM_THREADS:=1}"
: "${MKL_NUM_THREADS:=1}"
: "${MALLOC_ARENA_MAX:=2}"
export OPENBLAS_NUM_THREADS OMP_NUM_THREADS NUMEXPR_NUM_THREADS GOTO_NUM_THREADS MKL_NUM_THREADS MALLOC_ARENA_MAX

START_CMD="gunicorn -w 1 --threads 1 -b 0.0.0.0:5000 app:app"
if [[ -z "${START_CMD}" ]]; then
  START_CMD="gunicorn -w 1 --threads 1 -b 0.0.0.0:5000 app:app"
fi

if [[ "${START_CMD}" == *"127.0.0.1"* ]]; then
  echo "[WARN] 启动命令监听 127.0.0.1，建议改为 0.0.0.0 以便容器端口映射可达。"
fi

echo "[INFO] exec: ${START_CMD}"
exec bash -lc "${START_CMD}"
