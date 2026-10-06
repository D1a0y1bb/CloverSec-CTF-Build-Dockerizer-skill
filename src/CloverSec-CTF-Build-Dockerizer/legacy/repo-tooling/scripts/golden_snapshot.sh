#!/bin/bash
set -euo pipefail

python3 "$(dirname "$0")/golden_snapshot.py" "$@"
