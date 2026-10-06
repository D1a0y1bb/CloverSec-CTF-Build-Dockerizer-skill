#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
START_SECONDS="$SECONDS"

cd "$ROOT_DIR"

echo "[1/4] Python syntax"
python3 -m py_compile src/CloverSec-CTF-Build-Dockerizer/scripts/*.py scripts/*.py

echo "[2/4] Shell syntax"
find scripts src/CloverSec-CTF-Build-Dockerizer/scripts -name '*.sh' -print0 | xargs -0 -n1 bash -n

echo "[3/4] Documentation guard"
bash scripts/doc_guard.sh

echo "[4/4] Git whitespace check"
git diff --check

echo "Fast check passed in $((SECONDS - START_SECONDS))s"
