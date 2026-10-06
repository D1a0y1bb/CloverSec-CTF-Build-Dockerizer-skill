#!/usr/bin/env bash
set -euo pipefail

cid="$1"

docker exec "$cid" bash -lc "echo > /dev/tcp/127.0.0.1/3000"
docker exec "$cid" bash -lc "echo > /dev/tcp/127.0.0.1/3001"

echo "[ASSERT] node-multiport ports 3000/3001 are reachable inside container"
