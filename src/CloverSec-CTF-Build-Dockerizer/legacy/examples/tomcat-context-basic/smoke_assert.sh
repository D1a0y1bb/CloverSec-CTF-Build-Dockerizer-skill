#!/usr/bin/env bash
set -euo pipefail

cid="$1"
host_port="$2"

python3 - "${host_port}" <<'PY'
import sys
import urllib.request

url = f"http://127.0.0.1:{sys.argv[1]}/appctx/"
with urllib.request.urlopen(url, timeout=10) as resp:
    body = resp.read().decode("utf-8", errors="ignore")
if "ok:tomcat-context:/appctx" not in body:
    raise SystemExit(f"unexpected body from {url}: {body!r}")
print(f"[ASSERT] tomcat context ok: {url}")
PY
