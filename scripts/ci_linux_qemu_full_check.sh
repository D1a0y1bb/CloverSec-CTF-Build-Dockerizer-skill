#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MANUAL_CASE="${CI_LINUX_QEMU_MANUAL_CASE:-Build_test/linux-qemu-real-fragnesia/manual_case.yaml}"
POLICY="${CI_LINUX_QEMU_FULL_POLICY:-auto}" # auto|required|skip
MODE="${CI_LINUX_QEMU_FULL_MODE:-full}"
SUMMARY_PATH="${CI_LINUX_QEMU_JSON_SUMMARY:-/tmp/linux-qemu-ci-full.json}"
CASE_DIR_OVERRIDE="${CI_LINUX_QEMU_CASE_DIR:-}"
CASE_TAR="${CI_LINUX_QEMU_CASE_TAR:-}"
CASE_URL="${CI_LINUX_QEMU_CASE_URL:-}"
CASE_SUBDIR="${CI_LINUX_QEMU_CASE_SUBDIR:-}"
ASSET_MANIFEST_OVERRIDE="${CI_LINUX_QEMU_ASSET_MANIFEST:-}"
HOST_PORT_OVERRIDE="${CI_LINUX_QEMU_HOST_PORT:-}"
TIMEOUT_OVERRIDE="${CI_LINUX_QEMU_TIMEOUT_SECONDS:-}"
FLAG_OVERRIDE="${CI_LINUX_QEMU_FLAG:-}"
POC_CMD="${CI_LINUX_QEMU_POC_CMD:-}"
REQUIRE_POC="${CI_LINUX_QEMU_REQUIRE_POC:-0}"
TMP_DIR=""

usage() {
  cat <<'USAGE'
Usage:
  bash scripts/ci_linux_qemu_full_check.sh

Environment:
  CI_LINUX_QEMU_FULL_POLICY=auto|required|skip
  CI_LINUX_QEMU_FULL_MODE=full|flag|boot|build|static|preflight
  CI_LINUX_QEMU_MANUAL_CASE=Build_test/linux-qemu-real-fragnesia/manual_case.yaml
  CI_LINUX_QEMU_CASE_DIR=/path/to/linux-qemu/code
  CI_LINUX_QEMU_CASE_TAR=/path/to/case.tar
  CI_LINUX_QEMU_CASE_URL=https://example.internal/case.tar
  CI_LINUX_QEMU_CASE_SUBDIR=code
  CI_LINUX_QEMU_ASSET_MANIFEST=Build_test/linux-qemu-real-fragnesia/asset_manifest.yaml
  CI_LINUX_QEMU_HOST_PORT=2222
  CI_LINUX_QEMU_TIMEOUT_SECONDS=300
  CI_LINUX_QEMU_FLAG=flag{ci-linux-qemu-check}
  CI_LINUX_QEMU_POC_CMD='...'
  CI_LINUX_QEMU_REQUIRE_POC=1
  CI_LINUX_QEMU_JSON_SUMMARY=/tmp/linux-qemu-ci-full.json

Policy:
  auto      run when assets are available, skip when they are not
  required  fail when assets are unavailable
  skip      do not run
USAGE
}

write_skip_summary() {
  local reason="$1"
  python3 - "$SUMMARY_PATH" "$POLICY" "$MODE" "$reason" <<'PY'
import json
import sys
from pathlib import Path

summary_path = Path(sys.argv[1])
policy, mode, reason = sys.argv[2:5]
payload = {
    "schema_version": "1.0",
    "ok": True,
    "skipped": True,
    "policy": policy,
    "mode": mode,
    "reason": reason,
}
summary_path.parent.mkdir(parents=True, exist_ok=True)
summary_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY
}

cleanup() {
  if [[ -n "$TMP_DIR" ]]; then
    rm -rf "$TMP_DIR"
  fi
}
trap cleanup EXIT

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[ERROR] unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

case "$POLICY" in
  auto|required|skip) ;;
  *)
    echo "[ERROR] invalid CI_LINUX_QEMU_FULL_POLICY: $POLICY" >&2
    exit 2
    ;;
esac

if [[ "$POLICY" == "skip" ]]; then
  echo "[INFO] Linux-QEMU full CI check skipped by policy"
  write_skip_summary "policy=skip"
  exit 0
fi

MANUAL_CASE_PATH="${ROOT_DIR}/${MANUAL_CASE}"
if [[ ! -f "$MANUAL_CASE_PATH" ]]; then
  echo "[ERROR] manual case file not found: $MANUAL_CASE_PATH" >&2
  exit 2
fi

eval "$(
  python3 - "$MANUAL_CASE_PATH" <<'PY'
import shlex
import sys
from pathlib import Path

try:
    import yaml
except ModuleNotFoundError:
    print("echo '[ERROR] PyYAML is required' >&2; exit 2")
    raise SystemExit

data = yaml.safe_load(Path(sys.argv[1]).read_text(encoding="utf-8")) or {}
expected = data.get("expected") or {}
ci = data.get("ci") or {}

def emit(name, value):
    print(f"{name}={shlex.quote(str(value or ''))}")

emit("CASE_DIR_DEFAULT", data.get("external_case_dir", ""))
emit("ASSET_MANIFEST_DEFAULT", data.get("asset_manifest", ""))
emit("HOST_PORT_DEFAULT", ci.get("host_port") or expected.get("host_port") or "2222")
emit("TIMEOUT_DEFAULT", ci.get("timeout_seconds") or "300")
emit("FLAG_DEFAULT", ci.get("flag") or "flag{ci-linux-qemu-check}")
emit("POC_CMD_DEFAULT", ci.get("poc_cmd") or "")
PY
)"

CASE_DIR="$CASE_DIR_OVERRIDE"
ASSET_MANIFEST="$ASSET_MANIFEST_OVERRIDE"
HOST_PORT="${HOST_PORT_OVERRIDE:-$HOST_PORT_DEFAULT}"
TIMEOUT_SECONDS="${TIMEOUT_OVERRIDE:-$TIMEOUT_DEFAULT}"
FLAG_VALUE="${FLAG_OVERRIDE:-$FLAG_DEFAULT}"
if [[ -z "$POC_CMD" ]]; then
  POC_CMD="$POC_CMD_DEFAULT"
fi

if [[ -n "$CASE_URL" ]]; then
  TMP_DIR="$(mktemp -d /tmp/linux-qemu-ci-case-XXXXXX)"
  archive="${TMP_DIR}/case.tar"
  curl -fsSL "$CASE_URL" -o "$archive"
  tar -xf "$archive" -C "$TMP_DIR"
  if [[ -n "$CASE_SUBDIR" ]]; then
    CASE_DIR="${TMP_DIR}/${CASE_SUBDIR}"
  else
    CASE_DIR="$(find "$TMP_DIR" -mindepth 1 -maxdepth 2 -type d -name code | head -n 1)"
  fi
elif [[ -n "$CASE_TAR" ]]; then
  TMP_DIR="$(mktemp -d /tmp/linux-qemu-ci-case-XXXXXX)"
  tar -xf "$CASE_TAR" -C "$TMP_DIR"
  if [[ -n "$CASE_SUBDIR" ]]; then
    CASE_DIR="${TMP_DIR}/${CASE_SUBDIR}"
  else
    CASE_DIR="$(find "$TMP_DIR" -mindepth 1 -maxdepth 2 -type d -name code | head -n 1)"
  fi
elif [[ -z "$CASE_DIR" ]]; then
  CASE_DIR="$CASE_DIR_DEFAULT"
fi

if [[ -z "$ASSET_MANIFEST" ]]; then
  ASSET_MANIFEST="${ROOT_DIR}/${ASSET_MANIFEST_DEFAULT}"
elif [[ "$ASSET_MANIFEST" != /* ]]; then
  ASSET_MANIFEST="${ROOT_DIR}/${ASSET_MANIFEST}"
fi

if [[ -z "$CASE_DIR" || ! -d "$CASE_DIR" ]]; then
  message="Linux-QEMU case assets are unavailable: ${CASE_DIR:-<empty>}"
  if [[ "$POLICY" == "auto" ]]; then
    echo "[INFO] ${message}; skipping full check"
    write_skip_summary "$message"
    exit 0
  fi
  echo "[ERROR] ${message}" >&2
  exit 2
fi

if [[ "$MODE" == "full" && "$REQUIRE_POC" == "1" && -z "$POC_CMD" ]]; then
  echo "[ERROR] CI_LINUX_QEMU_REQUIRE_POC=1 but no CI_LINUX_QEMU_POC_CMD or ci.poc_cmd is configured" >&2
  exit 2
fi

cmd=(
  bash "${ROOT_DIR}/scripts/linux_qemu_manual_check.sh"
  --mode "$MODE"
  --case-dir "$CASE_DIR"
  --host-port "$HOST_PORT"
  --timeout-seconds "$TIMEOUT_SECONDS"
  --flag "$FLAG_VALUE"
  --json-summary "$SUMMARY_PATH"
)

if [[ -n "$ASSET_MANIFEST" ]]; then
  cmd+=(--asset-manifest "$ASSET_MANIFEST")
fi
if [[ -n "$POC_CMD" ]]; then
  cmd+=(--poc-cmd "$POC_CMD")
fi

echo "[INFO] Running Linux-QEMU CI check"
echo "- mode: $MODE"
echo "- case_dir: $CASE_DIR"
echo "- asset_manifest: ${ASSET_MANIFEST:-<none>}"
echo "- host_port: $HOST_PORT"
echo "- summary: $SUMMARY_PATH"

"${cmd[@]}"
