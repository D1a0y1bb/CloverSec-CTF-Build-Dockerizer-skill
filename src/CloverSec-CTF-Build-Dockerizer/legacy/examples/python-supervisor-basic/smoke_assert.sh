#!/usr/bin/env bash
set -euo pipefail

cid="$1"

docker exec "$cid" bash -lc "echo > /dev/tcp/127.0.0.1/5000"
docker exec "$cid" bash -lc "echo > /dev/tcp/127.0.0.1/5001"

echo "[ASSERT] python-supervisor ports 5000/5001 are reachable inside container"
