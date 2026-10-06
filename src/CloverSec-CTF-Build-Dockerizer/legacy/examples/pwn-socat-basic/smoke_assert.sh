#!/usr/bin/env bash
set -euo pipefail

cid="$1"
host_port="$2"

docker exec "$cid" bash -lc "echo > /dev/tcp/127.0.0.1/10001"
bash -lc "echo > /dev/tcp/127.0.0.1/${host_port}"

echo "[ASSERT] pwn-socat port 10001 is reachable"
