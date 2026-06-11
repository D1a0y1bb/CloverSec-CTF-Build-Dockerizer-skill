#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VALIDATE_SH="${SCRIPT_DIR}/validate.sh"
VERIFY_ASSET_MANIFEST="${SCRIPT_DIR}/verify_asset_manifest.py"

MODE="preflight"
CASE_DIR=""
IMAGE=""
HOST_PORT="2222"
TIMEOUT_SECONDS="180"
FLAG_VALUE="flag{manual_linux_qemu_check}"
POC_CMD=""
JSON_SUMMARY=""
KEEP_CONTAINER="0"
CONTAINER_NAME=""
ASSET_MANIFEST=""
CHECKS_FILE="$(mktemp "/tmp/linux-qemu-manual-checks.XXXXXX")"
LOG_FILE="$(mktemp "/tmp/linux-qemu-manual-log.XXXXXX")"

usage() {
  cat <<'USAGE'
Usage:
  bash scripts/linux_qemu_manual_check.sh --case-dir <path> [options]

Modes:
  --mode preflight|static|build|boot|flag|full   default: preflight

Options:
  --case-dir <path>          Linux-QEMU delivery directory
  --image <name>             Docker image name, default: linux-qemu-manual:<case-dir-name>
  --host-port <port>         host port mapped to container port 22, default: 2222
  --timeout-seconds <n>      boot wait timeout, default: 180
  --flag <value>             dynamic flag used in flag/full mode
  --poc-cmd <cmd>            host-side PoC command for full mode
  --asset-manifest <path>    optional asset manifest with size/SHA256 checks
  --json-summary <path>      write machine-readable summary
  --keep-container           keep the container after boot/flag/full
  -h, --help                 show this help

The default preflight mode does not build Docker images and does not boot QEMU.
USAGE
}

record_check() {
  local name="$1"
  local ok="$2"
  local level="$3"
  local summary="$4"
  printf '%s\t%s\t%s\t%s\n' "$name" "$ok" "$level" "$summary" >>"$CHECKS_FILE"
  if [[ "$ok" == "true" ]]; then
    printf '[OK] %s: %s\n' "$name" "$summary" | tee -a "$LOG_FILE"
  else
    printf '[FAIL] %s: %s\n' "$name" "$summary" | tee -a "$LOG_FILE"
  fi
}

cleanup() {
  if [[ -n "$CONTAINER_NAME" && "$KEEP_CONTAINER" != "1" ]]; then
    docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
  fi
  rm -f "$CHECKS_FILE" "$LOG_FILE"
}
trap cleanup EXIT

finish() {
  local rc="$1"
  if [[ -n "$JSON_SUMMARY" ]]; then
    python3 - "$JSON_SUMMARY" "$MODE" "$CASE_DIR" "$IMAGE" "$HOST_PORT" "$CONTAINER_NAME" "$rc" "$CHECKS_FILE" <<'PY'
import json
import sys
from pathlib import Path

summary_path = Path(sys.argv[1])
mode, case_dir, image, host_port, container_name, rc = sys.argv[2:8]
checks_file = Path(sys.argv[8])

checks = []
if checks_file.exists():
    for line in checks_file.read_text(encoding="utf-8", errors="replace").splitlines():
        name, ok, level, summary = (line.split("\t", 3) + ["", "", "", ""])[:4]
        checks.append({
            "name": name,
            "ok": ok == "true",
            "level": level,
            "summary": summary,
        })

payload = {
    "schema_version": "1.0",
    "ok": int(rc) == 0,
    "mode": mode,
    "case_dir": case_dir,
    "image": image,
    "host_port": host_port,
    "container_name": container_name,
    "checks": checks,
}
summary_path.parent.mkdir(parents=True, exist_ok=True)
summary_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY
  fi
  exit "$rc"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode)
      MODE="$2"; shift 2 ;;
    --case-dir)
      CASE_DIR="$2"; shift 2 ;;
    --image)
      IMAGE="$2"; shift 2 ;;
    --host-port)
      HOST_PORT="$2"; shift 2 ;;
    --timeout-seconds)
      TIMEOUT_SECONDS="$2"; shift 2 ;;
    --flag)
      FLAG_VALUE="$2"; shift 2 ;;
    --poc-cmd)
      POC_CMD="$2"; shift 2 ;;
    --asset-manifest)
      ASSET_MANIFEST="$2"; shift 2 ;;
    --json-summary)
      JSON_SUMMARY="$2"; shift 2 ;;
    --keep-container)
      KEEP_CONTAINER="1"; shift ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      echo "[ERROR] unknown argument: $1" >&2
      usage >&2
      exit 2 ;;
  esac
done

case "$MODE" in
  preflight|static|build|boot|flag|full) ;;
  *)
    echo "[ERROR] invalid mode: $MODE" >&2
    exit 2 ;;
esac

if [[ -z "$CASE_DIR" ]]; then
  echo "[ERROR] --case-dir is required" >&2
  exit 2
fi

if [[ ! -d "$CASE_DIR" ]]; then
  echo "[ERROR] case directory not found: $CASE_DIR" >&2
  exit 2
fi

CASE_DIR="$(cd "$CASE_DIR" && pwd)"
if [[ -z "$ASSET_MANIFEST" && -f "$CASE_DIR/asset_manifest.yaml" ]]; then
  ASSET_MANIFEST="$CASE_DIR/asset_manifest.yaml"
fi
slugify() {
  printf '%s' "$1" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9_.-' '-' | sed 's/^-*//;s/-*$//'
}
CASE_SLUG="$(slugify "$(basename "$CASE_DIR")")"
if [[ -z "$CASE_SLUG" ]]; then
  CASE_SLUG="case"
fi
if [[ -z "$IMAGE" ]]; then
  IMAGE="linux-qemu-manual:${CASE_SLUG}"
fi
CONTAINER_NAME="linux-qemu-manual-${CASE_SLUG}-$$"

overall_ok="true"
require_ok() {
  if [[ "$2" != "true" ]]; then
    overall_ok="false"
  fi
  record_check "$@"
}

check_file() {
  local rel="$1"
  if [[ -f "$CASE_DIR/$rel" ]]; then
    require_ok "file:${rel}" "true" "preflight" "found"
  else
    require_ok "file:${rel}" "false" "preflight" "missing"
  fi
}

preflight() {
  if [[ -n "$ASSET_MANIFEST" ]]; then
    if python3 "$VERIFY_ASSET_MANIFEST" --manifest "$ASSET_MANIFEST" --base-dir "$CASE_DIR" >>"$LOG_FILE" 2>&1; then
      require_ok "asset-manifest" "true" "preflight" "asset manifest passed"
    else
      require_ok "asset-manifest" "false" "preflight" "asset manifest failed"
    fi
  fi

  check_file "Dockerfile"
  check_file "start.sh"
  check_file "changeflag.sh"
  check_file "challenge.yaml"
  check_file "vm/vmlinuz"
  check_file "vm/initrd.img"
  check_file "vm/rootfs.ext4"

  if command -v docker >/dev/null 2>&1; then
    if docker info >/dev/null 2>&1; then
      require_ok "docker" "true" "preflight" "docker daemon available"
    else
      require_ok "docker" "false" "preflight" "docker daemon unavailable"
    fi
  else
    require_ok "docker" "false" "preflight" "docker command not found"
  fi

  if [[ -e /dev/kvm ]]; then
    if [[ -r /dev/kvm && -w /dev/kvm ]]; then
      record_check "kvm" "true" "preflight" "/dev/kvm available"
    else
      record_check "kvm" "false" "preflight" "/dev/kvm exists but is not readable and writable"
    fi
  else
    record_check "kvm" "true" "preflight" "/dev/kvm missing; TCG expected"
  fi

  if command -v nc >/dev/null 2>&1; then
    if nc -z 127.0.0.1 "$HOST_PORT" >/dev/null 2>&1; then
      require_ok "host-port" "false" "preflight" "127.0.0.1:${HOST_PORT} is already in use"
    else
      require_ok "host-port" "true" "preflight" "127.0.0.1:${HOST_PORT} is free"
    fi
  else
    record_check "host-port" "true" "preflight" "nc not found; port availability not checked"
  fi
}

run_static() {
  if bash "$VALIDATE_SH" "$CASE_DIR/Dockerfile" "$CASE_DIR/start.sh" "$CASE_DIR/challenge.yaml" >>"$LOG_FILE" 2>&1; then
    require_ok "static-validate" "true" "static" "validate.sh passed"
  else
    require_ok "static-validate" "false" "static" "validate.sh failed; see log"
  fi
}

run_build() {
  if docker build -t "$IMAGE" "$CASE_DIR" >>"$LOG_FILE" 2>&1; then
    require_ok "docker-build" "true" "build" "image built: $IMAGE"
  else
    require_ok "docker-build" "false" "build" "docker build failed"
  fi
}

wait_for_ssh_banner() {
  local deadline=$((SECONDS + TIMEOUT_SECONDS))
  local banner=""
  while (( SECONDS < deadline )); do
    if exec 3<>"/dev/tcp/127.0.0.1/${HOST_PORT}" 2>/dev/null; then
      if IFS= read -r -t 3 banner <&3; then
        exec 3>&- 3<&-
        if [[ "$banner" == SSH-* ]]; then
          return 0
        fi
      else
        exec 3>&- 3<&-
      fi
    fi
    sleep 2
  done
  return 1
}

run_boot() {
  docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
  local docker_env=()
  case "$MODE" in
    flag|full)
      docker_env=(-e "FLAG=${FLAG_VALUE}" -e "CTF_FLAG=${FLAG_VALUE}")
      ;;
  esac
  if docker run -d --name "$CONTAINER_NAME" -p "127.0.0.1:${HOST_PORT}:22" "${docker_env[@]}" "$IMAGE" >>"$LOG_FILE" 2>&1; then
    require_ok "docker-run" "true" "boot" "container started: $CONTAINER_NAME"
  else
    require_ok "docker-run" "false" "boot" "container failed to start"
    return
  fi

  if wait_for_ssh_banner; then
    require_ok "guest-ssh" "true" "boot" "SSH banner observed on 127.0.0.1:${HOST_PORT}"
  else
    docker logs "$CONTAINER_NAME" >>"$LOG_FILE" 2>&1 || true
    require_ok "guest-ssh" "false" "boot" "SSH banner not observed within ${TIMEOUT_SECONDS}s"
  fi
}

run_flag_check() {
  if [[ -z "$CONTAINER_NAME" ]]; then
    require_ok "flag-container" "false" "flag" "container is not running"
    return
  fi

  local outer_flag
  outer_flag="$(docker exec "$CONTAINER_NAME" bash -lc 'cat /flag 2>/dev/null' 2>>"$LOG_FILE" | tr -d '\r' | tail -n 1 || true)"
  if [[ "$outer_flag" == "$FLAG_VALUE" ]]; then
    require_ok "changeflag" "true" "flag" "/start.sh applied dynamic flag before QEMU boot"
  else
    require_ok "changeflag" "false" "flag" "container /flag does not match dynamic flag"
    return
  fi

  local actual
  actual="$(docker exec "$CONTAINER_NAME" bash -lc 'rootfs="$(find /opt -path "*/vm/rootfs.ext4" -type f | head -n 1)"; test -n "$rootfs"; debugfs -R "cat /root/flag" "$rootfs" 2>/dev/null' 2>>"$LOG_FILE" | tr -d '\r' | tail -n 1 || true)"
  if [[ "$actual" == "$FLAG_VALUE" ]]; then
    require_ok "guest-flag" "true" "flag" "guest /root/flag matches dynamic flag"
  else
    require_ok "guest-flag" "false" "flag" "guest /root/flag mismatch"
  fi
}

run_poc() {
  if [[ -z "$POC_CMD" ]]; then
    record_check "poc" "true" "challenge" "no poc command provided"
    return
  fi
  if CASE_DIR="$CASE_DIR" HOST_PORT="$HOST_PORT" IMAGE="$IMAGE" CONTAINER_NAME="$CONTAINER_NAME" FLAG="$FLAG_VALUE" bash -lc "$POC_CMD" >>"$LOG_FILE" 2>&1; then
    require_ok "poc" "true" "challenge" "poc command passed"
  else
    require_ok "poc" "false" "challenge" "poc command failed"
  fi
}

preflight

if [[ "$overall_ok" != "true" ]]; then
  case "$MODE" in
    build|boot|flag|full)
      finish 1
      ;;
  esac
fi

case "$MODE" in
  preflight)
    ;;
  static)
    run_static
    ;;
  build)
    run_build
    ;;
  boot)
    run_build
    [[ "$overall_ok" == "true" ]] || finish 1
    run_boot
    ;;
  flag)
    run_build
    [[ "$overall_ok" == "true" ]] || finish 1
    run_boot
    [[ "$overall_ok" == "true" ]] || finish 1
    run_flag_check
    ;;
  full)
    run_build
    [[ "$overall_ok" == "true" ]] || finish 1
    run_boot
    [[ "$overall_ok" == "true" ]] || finish 1
    run_flag_check
    [[ "$overall_ok" == "true" ]] || finish 1
    run_poc
    ;;
esac

if [[ "$overall_ok" == "true" ]]; then
  finish 0
fi
finish 1
