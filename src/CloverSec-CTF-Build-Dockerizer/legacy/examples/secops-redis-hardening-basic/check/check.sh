#!/bin/bash
set -euo pipefail

TARGET_IP="${1:-${TARGET_IP:-${TARGET_HOST:-127.0.0.1}}}"
TARGET_PORT="${2:-${TARGET_PORT:-6379}}"
TARGET_PASSWORD="${REDIS_PASSWORD:-CloverSec123!}"

python3 - "$TARGET_IP" "$TARGET_PORT" "$TARGET_PASSWORD" <<'PY'
import socket
import sys

host = sys.argv[1]
port = int(sys.argv[2])
password = sys.argv[3]


def send(parts):
    payload = f"*{len(parts)}\r\n".encode()
    for part in parts:
        blob = str(part).encode()
        payload += f"${len(blob)}\r\n".encode() + blob + b"\r\n"
    return payload


def recv(sock):
    return sock.recv(4096).decode("utf-8", errors="ignore")

# Unauthenticated ping must fail once password hardening is enabled.
with socket.create_connection((host, port), timeout=5) as sock:
    sock.sendall(send(["PING"]))
    data = recv(sock)
    if "+PONG" in data:
        print("[CHECK] unauthenticated PING unexpectedly succeeded")
        raise SystemExit(1)

with socket.create_connection((host, port), timeout=5) as sock:
    sock.sendall(send(["AUTH", password]))
    auth = recv(sock)
    if "+OK" not in auth:
        print("[CHECK] AUTH failed")
        raise SystemExit(1)
    sock.sendall(send(["PING"]))
    pong = recv(sock)
    if "+PONG" not in pong:
        print("[CHECK] authenticated PING failed")
        raise SystemExit(1)

print(f"[CHECK] Redis auth hardening OK on {host}:{port}")
PY
