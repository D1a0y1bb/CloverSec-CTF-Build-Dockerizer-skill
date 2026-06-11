#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
用法：
  bash scripts/validate.sh [--fix] [--fix-write] [--fix-loopback] [--static-only] [--with-dynamic-flag] [--json-summary path] Dockerfile start.sh [challenge.yaml]

说明：
  - 先执行平台硬规则，再执行 data/validate_rules.yaml 可配置规则。
  - 输出分级检查结果：ERROR/WARN/INFO
  - 有 ERROR 时退出码为 1；否则退出 0
  - --fix 仅预览安全自动修复（dry-run，不落盘）
  - --fix-write 应用安全自动修复（落盘）并继续校验
  - --fix-loopback 允许自动修复将显式 loopback 绑定参数改为 0.0.0.0
  - --static-only 只执行静态契约检查，不执行动态 flag 写入检查
  - --with-dynamic-flag 执行动态 flag 写入检查（当前默认开启，显式传入用于记录意图）
  - --json-summary 写入机器可读校验摘要
USAGE
}

AUTOFIX_MODE="false"
AUTOFIX_WRITE="false"
AUTOFIX_LOOPBACK="false"
JSON_SUMMARY_PATH=""
VALIDATION_LAYER="contract+dynamic-flag"
DYNAMIC_FLAG_CHECK="true"
POSITIONAL_ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --fix)
      AUTOFIX_MODE="true"
      shift
      ;;
    --fix-write)
      AUTOFIX_MODE="true"
      AUTOFIX_WRITE="true"
      shift
      ;;
    --fix-loopback)
      AUTOFIX_LOOPBACK="true"
      shift
      ;;
    --static-only)
      VALIDATION_LAYER="contract-static"
      DYNAMIC_FLAG_CHECK="false"
      shift
      ;;
    --with-dynamic-flag)
      VALIDATION_LAYER="contract+dynamic-flag"
      DYNAMIC_FLAG_CHECK="true"
      shift
      ;;
    --json-summary)
      if [[ $# -lt 2 || -z "${2:-}" ]]; then
        echo "[ERROR] --json-summary 需要路径参数" >&2
        exit 2
      fi
      JSON_SUMMARY_PATH="$2"
      shift 2
      ;;
    --)
      shift
      while [[ $# -gt 0 ]]; do
        POSITIONAL_ARGS+=("$1")
        shift
      done
      ;;
    -*)
      echo "[ERROR] 未知参数: $1" >&2
      usage
      exit 2
      ;;
    *)
      POSITIONAL_ARGS+=("$1")
      shift
      ;;
  esac
done

if [[ ${#POSITIONAL_ARGS[@]} -lt 2 || ${#POSITIONAL_ARGS[@]} -gt 3 ]]; then
  usage
  exit 2
fi

DOCKERFILE="${POSITIONAL_ARGS[0]}"
START_SH="${POSITIONAL_ARGS[1]}"
CHALLENGE_YAML="${POSITIONAL_ARGS[2]:-}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
RULES_FILE="${SKILL_ROOT}/data/validate_rules.yaml"
ALLOWLIST_FILE="${SKILL_ROOT}/data/base_image_allowlist.yaml"
AUTOFIX_SCRIPT="${SCRIPT_DIR}/autofix.py"
VALIDATE_CONTEXT_PY="${SCRIPT_DIR}/validate_context.py"
VALIDATE_ENFORCE_DIGEST="${VALIDATE_ENFORCE_DIGEST:-0}"

RDG_ENABLE_TTYD_CFG="true"
RDG_ENABLE_SSHD_CFG="true"
RDG_SSHD_PASSWORD_AUTH_CFG="true"
RDG_TTYD_INSTALL_FALLBACK_CFG="true"
RDG_CTF_USER_CFG="ctf"
RDG_CTF_IN_ROOT_GROUP_CFG="false"
RDG_SCORING_MODE_CFG="check_service"
RDG_INCLUDE_FLAG_ARTIFACT_CFG="true"
RDG_CHECK_ENABLED_CFG="true"
RDG_CHECK_SCRIPT_PATH_CFG="check/check.sh"
RDG_WORKDIR_CFG="/app"
ALLOW_LOOPBACK_BIND_CFG="false"
PROFILE_CFG="jeopardy"
FLAG_OPTIONAL_CFG="false"
STACK_CFG=""
SUPPORT_LEVEL_CFG="supported"
VM_ACCELERATOR_CFG="tcg"
VM_REQUIRE_KVM_CFG="false"
VM_KERNEL_CFG="vm/vmlinuz"
VM_INITRD_CFG="vm/initrd.img"
VM_ROOTFS_CFG="vm/rootfs.ext4"
VM_ASSET_MODE_CFG="prebuilt"
VM_FLAG_INJECTION_CFG="debugfs"
VM_GUEST_FLAG_PATH_CFG="/root/flag"
VM_HOSTFWD_PORTS_CFG=""
FLAG_SYNC_PATHS_CFG=""
HAS_SOLVE_PROBE_CFG="false"

if [[ ! -f "$DOCKERFILE" ]]; then
  echo "[ERROR] Dockerfile 不存在: $DOCKERFILE" >&2
  exit 2
fi

if [[ ! -f "$START_SH" ]]; then
  echo "[ERROR] start.sh 不存在: $START_SH" >&2
  exit 2
fi

if [[ ! -f "$RULES_FILE" ]]; then
  echo "[ERROR] 规则文件不存在: $RULES_FILE" >&2
  exit 2
fi

if [[ "$AUTOFIX_MODE" == "true" ]]; then
  if [[ ! -x "$AUTOFIX_SCRIPT" ]]; then
    echo "[ERROR] autofix 脚本不存在或不可执行: $AUTOFIX_SCRIPT" >&2
    exit 2
  fi
  autofix_args=(--dockerfile "$DOCKERFILE" --start-sh "$START_SH")
  if [[ -n "$CHALLENGE_YAML" ]]; then
    autofix_args+=(--challenge "$CHALLENGE_YAML")
  fi
  if [[ "$AUTOFIX_WRITE" == "true" ]]; then
    autofix_args+=(--write)
  fi
  if [[ "$AUTOFIX_LOOPBACK" == "true" ]]; then
    autofix_args+=(--loopback)
  fi
  echo "[INFO] 执行 autofix（mode=$([[ "$AUTOFIX_WRITE" == "true" ]] && echo write || echo dry-run)）"
  python3 "$AUTOFIX_SCRIPT" "${autofix_args[@]}"
fi

ERROR_COUNT=0
WARN_COUNT=0
INFO_COUNT=0
CHECK_COUNT=0

log_result() {
  local level="$1"
  local message="$2"
  CHECK_COUNT=$((CHECK_COUNT + 1))

  case "$level" in
    ERROR)
      ERROR_COUNT=$((ERROR_COUNT + 1))
      ;;
    WARN)
      WARN_COUNT=$((WARN_COUNT + 1))
      ;;
    INFO)
      INFO_COUNT=$((INFO_COUNT + 1))
      ;;
  esac

  printf '[%s] %s\n' "$level" "$message"
}

write_json_summary() {
  local exit_code="$1"
  local code="$2"
  local summary="$3"

  if [[ -z "$JSON_SUMMARY_PATH" ]]; then
    return
  fi

  python3 - "$JSON_SUMMARY_PATH" "$exit_code" "$code" "$summary" \
    "$CHECK_COUNT" "$ERROR_COUNT" "$WARN_COUNT" "$INFO_COUNT" \
    "$DOCKERFILE" "$START_SH" "$CHALLENGE_YAML" "$SUPPORT_LEVEL_CFG" \
    "$VALIDATION_LAYER" "$DYNAMIC_FLAG_CHECK" <<'PY'
import json
import sys
from pathlib import Path

(
    out,
    exit_code,
    code,
    summary,
    checks,
    errors,
    warns,
    infos,
    dockerfile,
    start_sh,
    challenge,
    support_level,
    validation_layer,
    dynamic_flag_check,
) = sys.argv[1:]
payload = {
    "ok": int(exit_code) == 0,
    "stage": "validate",
    "code": code,
    "level": "error" if int(exit_code) else "info",
    "summary": summary,
    "file": challenge or dockerfile,
    "hint": "",
    "autofixable": False,
    "support_level": support_level,
    "verification": {
        "level": validation_layer,
        "dynamic_flag_check": dynamic_flag_check == "true",
        "manual_required": validation_layer == "contract-static",
    },
    "counts": {
        "checks": int(checks),
        "errors": int(errors),
        "warnings": int(warns),
        "info": int(infos),
    },
    "inputs": {
        "dockerfile": dockerfile,
        "start_sh": start_sh,
        "challenge_yaml": challenge,
    },
}
path = Path(out)
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY
}

contains_re() {
  local file="$1"
  local pattern="$2"
  grep -Eiq -- "$pattern" "$file"
}

extract_base_image() {
  local from_line
  from_line="$(grep -Ei '^[[:space:]]*FROM[[:space:]]+' "$DOCKERFILE" | head -n1 || true)"
  if [[ -z "$from_line" ]]; then
    echo ""
    return
  fi

  # shellcheck disable=SC2206
  local parts=($from_line)
  local idx
  for ((idx = 1; idx < ${#parts[@]}; idx++)); do
    if [[ "${parts[$idx]}" == --* ]]; then
      continue
    fi
    echo "${parts[$idx]}"
    return
  done
  echo ""
}

is_digest_pinned_image() {
  local image_ref="$1"
  [[ "$image_ref" == *"@sha256:"* ]]
}

is_allowlisted_base_image() {
  local image_ref="$1"

  if [[ ! -f "$ALLOWLIST_FILE" ]]; then
    return 1
  fi

  if ! command -v python3 >/dev/null 2>&1; then
    return 1
  fi

  python3 - "$ALLOWLIST_FILE" "$image_ref" <<'PY'
import re
import sys
from pathlib import Path

allowlist_path = Path(sys.argv[1])
image_ref = sys.argv[2].strip()

try:
    import yaml
except ModuleNotFoundError:
    raise SystemExit(1)

try:
    raw = yaml.safe_load(allowlist_path.read_text(encoding="utf-8")) or {}
except Exception:
    raise SystemExit(1)

patterns = raw.get("official_allowlist", [])
if not isinstance(patterns, list):
    raise SystemExit(1)

for item in patterns:
    if not isinstance(item, str):
        continue
    item = item.strip()
    if not item:
        continue
    try:
        if re.search(item, image_ref):
            raise SystemExit(0)
    except re.error:
        continue

raise SystemExit(1)
PY
}

legacy_runtime_hint() {
  local image_ref="$1"
  case "$image_ref" in
    php:5.6-apache|php:5.6-apache@*)
      echo "PHP 5.6 已 EOL。仅建议用于历史题目兼容；新题目建议 php:8.2-apache。"
      return 0
      ;;
    php:7.4-apache|php:7.4-apache@*)
      echo "PHP 7.4 已 EOL。仅建议用于历史题目兼容；新题目建议 php:8.2-apache。"
      return 0
      ;;
    node:14-bullseye|node:14-bullseye@*)
      echo "Node 14 已 EOL。仅建议用于历史题目兼容；新题目建议 node:20-alpine 或 node:18-bookworm。"
      return 0
      ;;
    node:16-bullseye|node:16-bullseye@*)
      echo "Node 16 已 EOL。仅建议用于历史题目兼容；新题目建议 node:20-alpine 或 node:18-bookworm。"
      return 0
      ;;
    eclipse-temurin:8-jre-jammy|eclipse-temurin:8-jre-jammy@*)
      echo "JDK 8 运行时较老。仅建议用于历史题目兼容；新题目建议 eclipse-temurin:17-jre-jammy。"
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

is_multiservice_start() {
  if contains_re "$START_SH" '(^|[[:space:]])supervisord([[:space:]]|$)'; then
    return 0
  fi

  if contains_re "$START_SH" '(^|[[:space:]])service[[:space:]]+[A-Za-z0-9_.-]+[[:space:]]+start([[:space:]]|$)'; then
    return 0
  fi

  if contains_re "$START_SH" '(^|[[:space:]])(mysqld|mysqld_safe|mariadbd)([[:space:]]|$)'; then
    return 0
  fi

  if grep -Eq '[^&]&[[:space:]]*$' "$START_SH"; then
    return 0
  fi

  return 1
}

has_real_exec() {
  local lines
  lines="$(grep -E '^[[:space:]]*exec[[:space:]]+' "$START_SH" 2>/dev/null | grep -Evi 'tail[[:space:]]+-[fF][[:space:]]+/dev/null' || true)"
  [[ -n "$lines" ]]
}

has_service_start_cmd() {
  contains_re "$START_SH" '(^|[[:space:]])(service[[:space:]]+[A-Za-z0-9_.-]+[[:space:]]+start|mysqld|mysqld_safe|mariadbd|apache2ctl|nginx|supervisord|php-fpm|gunicorn|uvicorn|catalina\.sh|java|node|python)([[:space:]]|$)'
}

has_tail_dev_null() {
  contains_re "$START_SH" 'tail[[:space:]]+-[fF][[:space:]]+/dev/null'
}

find_unrendered_template_vars() {
  local changeflag_host
  changeflag_host="$(cd "$(dirname "$START_SH")" && pwd)/changeflag.sh"

  local files=("$DOCKERFILE" "$START_SH")
  if [[ -f "$changeflag_host" ]]; then
    files+=("$changeflag_host")
  fi

  grep -Eho '\{\{[A-Z0-9_]+\}\}' "${files[@]}" 2>/dev/null \
    | sort -u \
    | tr '\n' ' ' \
    | sed -E 's/[[:space:]]+$//' || true
}

validate_changeflag_dynamic_write() {
  local changeflag_host
  changeflag_host="$(cd "$(dirname "$START_SH")" && pwd)/changeflag.sh"

  if [[ ! -f "$changeflag_host" ]]; then
    log_result ERROR "changeflag.sh 不存在，无法验证动态 flag 写入。"
    return
  fi

  if contains_re "$changeflag_host" 'TARGET_FLAG=.*\$\{[^[:space:]]*flag\{'; then
    log_result ERROR "changeflag.sh 使用嵌套参数展开直接包含 flag{...} 默认值，传入动态 flag 时可能产生多余字符。修复：改用 if/elif/else 明确赋值。"
  else
    log_result INFO "changeflag.sh 未检测到 flag{...} 嵌套参数展开风险"
  fi

  if ! contains_re "$changeflag_host" 'FLAG_PATH'; then
    log_result WARN "changeflag.sh 未支持 FLAG_PATH，跳过隔离动态写入测试；建议支持 FLAG_PATH 以便验证和平台调试。"
    return
  fi

  local tmp_dir
  tmp_dir="$(mktemp -d "/tmp/ctf-changeflag-XXXXXX")"
  local expected="flag{validate_dynamic_flag}"
  local target="${tmp_dir}/flag"
  local stdout_file="${tmp_dir}/stdout.txt"
  local stderr_file="${tmp_dir}/stderr.txt"

  if FLAG_PATH="$target" FLAG_INJECTION=none CTFBUILD_SKIP_SYNC_PATHS=1 bash "$changeflag_host" "$expected" >"$stdout_file" 2>"$stderr_file"; then
    if [[ ! -f "$target" ]]; then
      log_result ERROR "changeflag.sh 执行成功但没有写入 FLAG_PATH 指定文件。"
    else
      local actual
      actual="$(tr -d '\r' < "$target" | sed -E 's/[[:space:]]+$//')"
      if [[ "$actual" == "$expected" ]]; then
        log_result INFO "changeflag.sh 动态 flag 写入测试通过"
      else
        log_result ERROR "changeflag.sh 动态 flag 写入不一致：期望 ${expected}，实际 ${actual}。"
      fi
    fi
  else
    log_result ERROR "changeflag.sh 动态 flag 写入测试执行失败。"
    if [[ -s "$stderr_file" ]]; then
      sed -n '1,5p' "$stderr_file" >&2 || true
    fi
  fi

  rm -rf "$tmp_dir"
}

has_background_ampersand() {
  grep -Eiq '(^|[^#].*)[^&]&[[:space:]]*$' "$START_SH"
}

has_wait_or_foreground_hold() {
  contains_re "$START_SH" '(^|[[:space:]])(wait|fg)([[:space:]]|$)'
}

has_public_frontend_entry() {
  if contains_re "$START_SH" 'apache2-foreground|apache2ctl[[:space:]]+-D[[:space:]]+FOREGROUND|httpd[[:space:]]+-D[[:space:]]+FOREGROUND|catalina\.sh[[:space:]]+run|nginx[[:space:]]+-g[[:space:]]+.*daemon[[:space:]]+off;'; then
    return 0
  fi
  if contains_re "$START_SH" '(gunicorn|uvicorn).*(0\.0\.0\.0|\-\-host[=[:space:]]*0\.0\.0\.0|\-b[[:space:]]*0\.0\.0\.0)'; then
    return 0
  fi
  return 1
}

uses_loopback_bind() {
  contains_re "$START_SH" '127\.0\.0\.1|localhost|bind-address=127\.0\.0\.1|--host[=[:space:]]*127\.0\.0\.1|--host[=[:space:]]*localhost|\-b[[:space:]]*127\.0\.0\.1'
}

extract_start_cmd_ports() {
  {
    grep -Eio -- '--port[=[:space:]]*[0-9]{1,5}' "$START_SH" 2>/dev/null | sed -E 's/.*[=[:space:]]([0-9]{1,5})/\1/' || true
    grep -Eio -- '\-b[[:space:]]*(0\.0\.0\.0|127\.0\.0\.1|localhost):[0-9]{1,5}' "$START_SH" 2>/dev/null | sed -E 's/.*:([0-9]{1,5})/\1/' || true
    grep -Eio -- 'runserver[[:space:]]+(0\.0\.0\.0|127\.0\.0\.1|localhost):[0-9]{1,5}' "$START_SH" 2>/dev/null | sed -E 's/.*:([0-9]{1,5})/\1/' || true
    grep -Eio -- 'listen\([[:space:]]*[0-9]{1,5}[[:space:]]*\)' "$START_SH" 2>/dev/null | sed -E 's/[^0-9]*([0-9]{1,5}).*/\1/' || true
  } | awk 'NF' | sort -u
}

extract_tcpserver_port_from_start() {
  grep -Eio 'tcpserver[[:space:]]+(-[[:alnum:]]+[[:space:]]+)*((0\.0\.0\.0|127\.0\.0\.1|localhost)[[:space:]]+)?[0-9]{1,5}' "$START_SH" \
    | head -n1 \
    | grep -Eo '[0-9]{1,5}$' || true
}

extract_socat_port_from_start() {
  grep -Eio 'socat[[:space:]]+[^[:space:]]*TCP-LISTEN:[0-9]{1,5}' "$START_SH" \
    | head -n1 \
    | sed -E 's/.*TCP-LISTEN:([0-9]{1,5}).*/\1/' || true
}

escape_regex() {
  printf '%s' "$1" | sed -E 's/[][(){}.^$*+?|\\]/\\&/g'
}

parse_challenge_ports() {
  local file="$1"

  {
    grep -E '^[[:space:]]*expose_ports:[[:space:]]*\[.*\][[:space:]]*$' "$file" 2>/dev/null \
      | sed -E 's/^[[:space:]]*expose_ports:[[:space:]]*\[(.*)\][[:space:]]*$/\1/' \
      | tr ',' '\n' \
      | sed -E "s/[\"'[:space:]]//g" \
      | awk 'NF' || true

    awk '
      BEGIN { in_block=0 }
      {
        line=$0
        gsub("\r", "", line)

        if (line ~ /^[[:space:]]*expose_ports:[[:space:]]*$/) {
          in_block=1
          next
        }

        if (in_block == 1) {
          if (line ~ /^[[:space:]]*-[[:space:]]*/) {
            gsub(/^[[:space:]]*-[[:space:]]*/, "", line)
            gsub(/["\047[:space:]]/, "", line)
            if (line != "") print line
            next
          }

          if (line ~ /^[[:space:]]*[A-Za-z0-9_]+:[[:space:]]*/) {
            in_block=0
            next
          }
        }
      }
    ' "$file" | awk 'NF'
  } | sort -u
}

parse_challenge_stack() {
  local file="$1"
  if [[ ! -f "$file" ]]; then
    echo ""
    return
  fi

  awk '
    BEGIN { stack="" }
    /^[[:space:]]*stack:[[:space:]]*/ {
      line=$0
      sub(/^[[:space:]]*stack:[[:space:]]*/, "", line)
      gsub(/["\047[:space:]]/, "", line)
      if (line != "") {
        stack=line
        print stack
        exit
      }
    }
  ' "$file"
}

load_challenge_v2_context() {
  if [[ -z "$CHALLENGE_YAML" ]]; then
    return
  fi

  if ! command -v python3 >/dev/null 2>&1; then
    log_result ERROR "CONFIG_CONTEXT_PARSE_FAILED: 未找到 python3"
    return 2
  fi

  if [[ ! -f "$VALIDATE_CONTEXT_PY" ]]; then
    log_result ERROR "CONFIG_CONTEXT_PARSE_FAILED: validate_context.py 不存在: $VALIDATE_CONTEXT_PY"
    return 2
  fi

  local context_lines=""
  if ! context_lines="$(python3 "$VALIDATE_CONTEXT_PY" "$CHALLENGE_YAML" 2>&1)"; then
    local one_line
    one_line="$(printf '%s' "$context_lines" | tr '\n' ' ' | sed -E 's/[[:space:]]+/ /g')"
    log_result ERROR "${one_line:-CONFIG_CONTEXT_PARSE_FAILED}"
    return 2
  fi

  local line
  while IFS= read -r line; do
    [[ -n "$line" ]] || continue
    eval "$line"
  done <<< "$context_lines"
}

parse_challenge_key_value() {
  local file="$1"
  local key="$2"
  local default="$3"

  if [[ ! -f "$file" ]]; then
    echo "$default"
    return
  fi

  local line
  line="$(grep -E "^[[:space:]]*${key}:[[:space:]]*" "$file" | head -n1 || true)"
  if [[ -z "$line" ]]; then
    echo "$default"
    return
  fi

  local value
  value="${line#*:}"
  value="$(printf '%s' "$value" | sed -E "s/^[[:space:]]*//; s/[\"']//g; s/[[:space:]]*$//")"
  if [[ -z "$value" ]]; then
    echo "$default"
  else
    echo "$value"
  fi
}

normalize_bool_text() {
  local raw="$1"
  local default="$2"
  local lower
  lower="$(printf '%s' "$raw" | tr '[:upper:]' '[:lower:]')"
  case "$lower" in
    true|1|yes|y)
      echo "true"
      ;;
    false|0|no|n)
      echo "false"
      ;;
    *)
      echo "$default"
      ;;
  esac
}

load_rdg_config_from_challenge() {
  if [[ -z "$CHALLENGE_YAML" ]]; then
    return
  fi
  load_challenge_v2_context
}

parse_docker_expose_ports() {
  grep -Ei '^[[:space:]]*EXPOSE[[:space:]]+' "$DOCKERFILE" \
    | sed -E 's/^[[:space:]]*EXPOSE[[:space:]]+//' \
    | tr ' ' '\n' \
    | sed -E 's#/.*$##' \
    | awk 'NF' \
    | sort -u || true
}

infer_stack_hint() {
  local stack=""
  if [[ -n "$CHALLENGE_YAML" ]]; then
    stack="$(parse_challenge_stack "$CHALLENGE_YAML" || true)"
  fi

  if [[ -n "$stack" ]]; then
    echo "$stack"
    return
  fi

  if contains_re "$START_SH" 'qemu-system-' || contains_re "$DOCKERFILE" 'qemu-system-|qemu-utils'; then
    echo "linux-qemu"
    return
  fi

  if contains_re "$DOCKERFILE" 'server\.xml|redis\.conf|my\.cnf|sshd_config' || contains_re "$START_SH" 'secops|redis-server|/usr/sbin/sshd -D -e'; then
    echo "secops"
    return
  fi

  if contains_re "$START_SH" 'ttyd' || contains_re "$DOCKERFILE" '(^|[^A-Za-z0-9_-])(ttyd|useradd[[:space:]]+.*ctf)([^A-Za-z0-9_-]|$)'; then
    echo "rdg"
    return
  fi

  if contains_re "$START_SH" 'xinetd|ctf\.xinetd|tcpserver|socat' || contains_re "$DOCKERFILE" 'xinetd|ucspi-tcp6|tcpserver|socat'; then
    echo "pwn"
    return
  fi

  if contains_re "$START_SH" 'gunicorn|uvicorn' || contains_re "$DOCKERFILE" 'transformers|OPENBLAS_NUM_THREADS|python'; then
    echo "ai"
    return
  fi

  echo ""
}

extract_xinetd_port_from_context() {
  local base_dir
  base_dir="$(cd "$(dirname "$DOCKERFILE")" && pwd)"
  local cfg_files=("${base_dir}/ctf.xinetd" "${base_dir}/xinetd.conf")
  local f
  for f in "${cfg_files[@]}"; do
    [[ -f "$f" ]] || continue
    local port
    port="$(grep -Eio 'port[[:space:]]*=[[:space:]]*[0-9]+' "$f" | head -n1 | sed -E 's/.*=[[:space:]]*([0-9]+).*/\1/' || true)"
    if [[ -n "$port" ]]; then
      echo "$port"
      return
    fi
  done
  echo ""
}

parse_qemu_hostfwd_ports() {
  grep -Eho 'hostfwd=tcp::[0-9]+-:[0-9]+' "$START_SH" "$DOCKERFILE" 2>/dev/null \
    | sed -E 's/^hostfwd=tcp::([0-9]+)-:[0-9]+$/\1/' \
    | awk 'NF' \
    | sort -u || true
}

extract_qemu_binary_from_start() {
  grep -E '^[[:space:]]*QEMU_BINARY=' "$START_SH" 2>/dev/null \
    | head -n1 \
    | sed -E 's/^[[:space:]]*QEMU_BINARY=["'\'']?([^"'\'']+)["'\'']?.*$/\1/' || true
}

qemu_package_for_binary() {
  local binary="$1"
  case "$binary" in
    qemu-system-x86_64|qemu-system-i386)
      echo "qemu-system-x86"
      ;;
    qemu-system-aarch64|qemu-system-arm)
      echo "qemu-system-arm"
      ;;
    *)
      echo ""
      ;;
  esac
}

csv_to_lines() {
  local csv="$1"
  printf '%s' "$csv" | tr ',' '\n' | awk 'NF' | sort -u
}

rule_scope_file() {
  local scope="$1"
  case "$scope" in
    Dockerfile|dockerfile)
      echo "$DOCKERFILE"
      ;;
    start.sh|start|start_sh)
      echo "$START_SH"
      ;;
    *)
      echo ""
      ;;
  esac
}

run_hard_rules() {
  echo "[A] 平台必需硬规则"

  local stack_cfg=""
  if [[ -n "$CHALLENGE_YAML" && -f "$CHALLENGE_YAML" ]]; then
    stack_cfg="$(parse_challenge_stack "$CHALLENGE_YAML" || true)"
  fi
  local rdg_flag_optional=0
  if [[ "$FLAG_OPTIONAL_CFG" == "true" ]]; then
    rdg_flag_optional=1
  fi

  if contains_re "$DOCKERFILE" '^[[:space:]]*(COPY|ADD)[[:space:]].*start\.sh.*(/start\.sh|"/start\.sh")'; then
    log_result INFO "Dockerfile 已将 start.sh 放置到 /start.sh"
  else
    log_result ERROR "未检测到 /start.sh 拷贝逻辑。修复：在 Dockerfile 增加 COPY start.sh /start.sh。"
  fi

  if contains_re "$DOCKERFILE" '^[[:space:]]*(COPY|ADD)[[:space:]].*changeflag\.sh.*(/changeflag\.sh|"/changeflag\.sh")'; then
    log_result INFO "Dockerfile 已将 changeflag.sh 放置到 /changeflag.sh"
  else
    log_result ERROR "未检测到 /changeflag.sh 拷贝逻辑。修复：在 Dockerfile 增加 COPY changeflag.sh /changeflag.sh。"
  fi

  if [[ $rdg_flag_optional -eq 1 ]]; then
    log_result INFO "profile include_flag_artifact=false：放行 /flag 产物校验"
  else
    if contains_re "$DOCKERFILE" '^[[:space:]]*(COPY|ADD)[[:space:]].*flag.*(/flag|"/flag")' \
      || contains_re "$DOCKERFILE" '^[[:space:]]*RUN[[:space:]].*(touch|echo|printf|install).*([[:space:]]|>)\/flag'; then
      log_result INFO "Dockerfile 已创建或复制 /flag"
    else
      log_result ERROR "未检测到 /flag 创建逻辑。修复：增加 COPY flag /flag 或 RUN touch /flag。"
    fi
  fi

  if contains_re "$DOCKERFILE" 'chmod.*(\+x|a\+x|u\+x|555|755|775).*/start\.sh'; then
    log_result INFO "Dockerfile 已对 /start.sh 设置可执行权限"
  else
    log_result ERROR "未检测到 /start.sh 可执行权限。修复：增加 RUN chmod 555 /start.sh。"
  fi

  if contains_re "$DOCKERFILE" 'chmod.*(\+x|a\+x|u\+x|555|755|775).*/changeflag\.sh'; then
    log_result INFO "Dockerfile 已对 /changeflag.sh 设置可执行权限"
  else
    log_result ERROR "未检测到 /changeflag.sh 可执行权限。修复：增加 RUN chmod 555 /changeflag.sh。"
  fi

  if [[ $rdg_flag_optional -eq 1 ]]; then
    log_result INFO "profile include_flag_artifact=false：放行 /flag 权限校验"
  else
    if contains_re "$DOCKERFILE" 'chmod.*(444|644|664|744|755|a\+r|u\+r|go\+r).*/flag'; then
      log_result INFO "Dockerfile 已对 /flag 设置可读权限"
    else
      log_result ERROR "未检测到 /flag 可读权限。修复：增加 RUN chmod 444 /flag。"
    fi
  fi

  FIRST_LINE="$(head -n1 "$START_SH" | tr -d '\r')"
  if [[ "$FIRST_LINE" == "#!/bin/bash" ]]; then
    log_result INFO "start.sh 首行是 #!/bin/bash"
  else
    log_result ERROR "start.sh 首行必须是 #!/bin/bash。修复：将 shebang 改为 #!/bin/bash。"
  fi

  local unrendered_vars
  unrendered_vars="$(find_unrendered_template_vars)"
  if [[ -n "$unrendered_vars" ]]; then
    log_result ERROR "渲染产物仍包含未替换模板变量: ${unrendered_vars}"
  else
    log_result INFO "渲染产物未发现残留模板变量"
  fi

  echo
  echo "[B] /bin/bash 可用性硬规则"

  BASE_IMAGE="$(extract_base_image)"
  HAS_BASH_INSTALL=0
  if contains_re "$DOCKERFILE" 'apk[[:space:]]+add.*bash'; then
    HAS_BASH_INSTALL=1
  fi
  if contains_re "$DOCKERFILE" 'apt-get[[:space:]]+install' \
    && contains_re "$DOCKERFILE" '(^|[^A-Za-z0-9_-])bash([^A-Za-z0-9_-]|$)'; then
    HAS_BASH_INSTALL=1
  fi
  if contains_re "$DOCKERFILE" '(yum|dnf)[[:space:]]+install' \
    && contains_re "$DOCKERFILE" '(^|[^A-Za-z0-9_-])bash([^A-Za-z0-9_-]|$)'; then
    HAS_BASH_INSTALL=1
  fi

  if [[ "$BASE_IMAGE" =~ ^bash([:@]|$) ]]; then
    log_result INFO "基础镜像为 bash 系列（默认包含 /bin/bash）"
  elif [[ $HAS_BASH_INSTALL -eq 1 ]]; then
    log_result INFO "Dockerfile 已显式安装 bash"
  else
    log_result ERROR "未检测到 bash 安装。修复：在 Dockerfile 安装 bash，确保 /bin/bash 可用。"
  fi
}

run_configurable_rules() {
  echo
  echo "[C] 可配置规则（validate_rules.yaml）"

  local has_python=0
  if command -v python3 >/dev/null 2>&1; then
    has_python=1
  fi

  if [[ $has_python -ne 1 ]]; then
    log_result ERROR "系统缺少 python3，无法解析 validate_rules.yaml"
    return
  fi

  if ! python3 - <<'PY' >/dev/null 2>&1; then
import yaml  # noqa: F401
PY
    log_result ERROR "缺少 PyYAML，无法加载 validate_rules.yaml。请先安装 scripts/requirements.txt。"
    return
  fi

  local delim
  delim=$'\037'

  while IFS="$delim" read -r rid level scope expect when_pat pattern message; do
    [[ -n "$rid" ]] || continue

    target_file="$(rule_scope_file "$scope")"
    if [[ -z "$target_file" ]]; then
      log_result WARN "规则 ${rid} 的 scope 无效：${scope}"
      continue
    fi

    # 条件门控：when 不满足时跳过
    if [[ -n "$when_pat" ]]; then
      if ! contains_re "$target_file" "$when_pat"; then
        continue
      fi
    fi

    expect_mode="${expect:-present}"

    matched=0
    if contains_re "$target_file" "$pattern"; then
      matched=1
    fi

    case "$expect_mode" in
      present)
        if [[ $matched -eq 0 ]]; then
          log_result "$level" "[${rid}] ${message}"
        else
          log_result INFO "[${rid}] 通过"
        fi
        ;;
      absent)
        if [[ $matched -eq 1 ]]; then
          log_result "$level" "[${rid}] ${message}"
        else
          log_result INFO "[${rid}] 通过"
        fi
        ;;
      match)
        if [[ $matched -eq 1 ]]; then
          log_result "$level" "[${rid}] ${message}"
        fi
        ;;
      *)
        log_result WARN "规则 ${rid} expect 字段无效：${expect_mode}"
        ;;
    esac
  done < <(
    python3 - "$RULES_FILE" <<'PY'
import sys
from pathlib import Path

path = Path(sys.argv[1])

import yaml

raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
rules = raw.get("rules", [])
if not isinstance(rules, list):
    raise SystemExit(0)

for rule in rules:
    if not isinstance(rule, dict):
        continue
    rid = str(rule.get("id", "")).strip()
    level = str(rule.get("level", "WARN")).strip().upper() or "WARN"
    scope = str(rule.get("scope", "")).strip()
    expect = str(rule.get("expect", "present")).strip()
    when_pat = str(rule.get("when", "")).strip()
    pattern = str(rule.get("pattern", "")).strip()
    message = str(rule.get("message", "")).strip().replace("\t", " ").replace("\n", " ")

    if not rid or not scope or not pattern:
        continue

    sep = "\x1f"
    print(sep.join([rid, level, scope, expect, when_pat, pattern, message]))
PY
  )
}

run_dynamic_checks() {
  echo
  echo "[D] 动态策略检查"

  validate_changeflag_dynamic_write

  WORKDIR_VALUE="$(grep -Ei '^[[:space:]]*WORKDIR[[:space:]]+' "$DOCKERFILE" | tail -n1 | awk '{print $2}' || true)"

  MULTISERVICE=0
  if is_multiservice_start; then
    MULTISERVICE=1
  fi

  if [[ -n "$WORKDIR_VALUE" ]]; then
    WORKDIR_RE="$(escape_regex "$WORKDIR_VALUE")"
    if grep -Eq "^[[:space:]]*cd[[:space:]]+\"?${WORKDIR_RE}\"?([[:space:]]|$)" "$START_SH"; then
      log_result INFO "start.sh 与 WORKDIR 保持一致（存在 cd ${WORKDIR_VALUE}）"
    else
      if [[ $MULTISERVICE -eq 1 ]]; then
        log_result WARN "未检测到 cd ${WORKDIR_VALUE}，多服务场景可接受但建议显式对齐"
      else
        log_result ERROR "WORKDIR 与 start.sh 路径不一致。修复：在 start.sh 增加 cd ${WORKDIR_VALUE}。"
      fi
    fi
  else
    log_result WARN "Dockerfile 未检测到 WORKDIR，建议显式声明"
  fi

  TAIL_DEV_NULL=0
  if has_tail_dev_null; then
    TAIL_DEV_NULL=1
  fi

  REAL_EXEC=0
  if has_real_exec; then
    REAL_EXEC=1
  fi

  HAS_SERVICE_CMD=0
  if has_service_start_cmd; then
    HAS_SERVICE_CMD=1
  fi

  if [[ $TAIL_DEV_NULL -eq 1 ]]; then
    if [[ $REAL_EXEC -eq 1 || $HAS_SERVICE_CMD -eq 1 ]]; then
      log_result WARN "检测到 tail -f /dev/null。当前服务可运行，但建议改为前台 exec 或 tail 真实日志文件。"
    else
      log_result ERROR "仅检测到 tail -f /dev/null 且无服务启动。修复：启动真实服务进程并以前台 exec 运行。"
    fi
  else
    log_result INFO "未检测到 tail -f /dev/null"
  fi

  if [[ $MULTISERVICE -eq 0 ]]; then
    if [[ $REAL_EXEC -eq 1 ]]; then
      log_result INFO "单服务场景已使用 exec 作为 PID1"
    else
      log_result ERROR "单服务未使用 exec 启动主进程。修复：将启动行改为 exec <主命令>。"
    fi
  else
    if [[ $REAL_EXEC -eq 1 ]]; then
      log_result INFO "多服务场景仍使用 exec 主进程，策略良好"
    elif [[ $HAS_SERVICE_CMD -eq 1 ]]; then
      log_result WARN "多服务场景未使用 exec；请确保前台进程与日志可观测"
    else
      log_result ERROR "多服务场景未检测到有效服务命令。修复：至少启动一个真实服务并保持前台进程。"
    fi
  fi

  local stack_hint
  stack_hint="$(infer_stack_hint)"
  if [[ -n "$stack_hint" ]]; then
    log_result INFO "检测到栈提示: ${stack_hint}"
  fi
  if [[ -n "$FLAG_SYNC_PATHS_CFG" ]]; then
    log_result INFO "业务 flag 同步路径已配置: ${FLAG_SYNC_PATHS_CFG}"
  elif [[ "$stack_hint" == "pwn" ]]; then
    log_result WARN "Pwn 题未配置 challenge.flag.sync_paths。validate.sh 只能确认 /flag 与平台契约，不能确认题目程序会读到动态 flag。"
  fi
  if [[ "$HAS_SOLVE_PROBE_CFG" == "true" ]]; then
    log_result INFO "检测到 verification.solve_probe；题目入口验证应在容器业务断言阶段执行。"
  else
    log_result INFO "validate.sh 只验证平台交付契约，不证明题目业务可解；需要 build/run 或 verification.solve_probe 证明题目入口可用。"
  fi

  local base_image
  base_image="$(extract_base_image)"
  if [[ -n "$base_image" ]]; then
    if is_digest_pinned_image "$base_image"; then
      log_result INFO "基础镜像已使用 digest 固定: ${base_image}"
    elif is_allowlisted_base_image "$base_image"; then
      log_result INFO "基础镜像命中官方白名单（tag-only 放行）: ${base_image}"
    else
      if [[ "$VALIDATE_ENFORCE_DIGEST" == "1" && "$SUPPORT_LEVEL_CFG" == "partial" ]]; then
        log_result WARN "support_level=partial：交付校验记录基础镜像未固定 digest（当前: ${base_image}），但不阻断原型样例。"
      elif [[ "$VALIDATE_ENFORCE_DIGEST" == "1" ]]; then
        log_result ERROR "交付校验要求基础镜像使用 digest（当前: ${base_image}）。修复：将 base_image 改为 image:tag@sha256:<digest>。"
      else
        log_result WARN "基础镜像未使用 digest 固定（当前: ${base_image}）。正式交付前建议 pin digest。"
      fi
    fi
  else
    log_result WARN "未检测到基础镜像 FROM，跳过 digest 校验"
  fi

  legacy_runtime_msg=""
  if legacy_runtime_msg="$(legacy_runtime_hint "$base_image")"; then
    log_result WARN "检测到 legacy 运行时镜像：${base_image}。${legacy_runtime_msg}"
  else
    log_result INFO "运行时镜像未命中 legacy 档位"
  fi

  local has_public_frontend=0
  if has_public_frontend_entry; then
    has_public_frontend=1
  fi

  if uses_loopback_bind; then
    if [[ "$ALLOW_LOOPBACK_BIND_CFG" == "true" ]]; then
      log_result INFO "challenge.platform.allow_loopback_bind=true：已按配置放行 localhost/127.0.0.1 监听。"
    elif [[ $has_public_frontend -eq 1 ]]; then
      log_result INFO "检测到公网前置入口且回环监听用于辅服务，按 SSRF/内网链路场景放行。"
    else
      log_result ERROR "检测到服务监听 localhost/127.0.0.1 且未配置豁免。修复：改监听 0.0.0.0 或设置 challenge.platform.allow_loopback_bind=true。"
    fi
  else
    log_result INFO "未检测到 localhost/127.0.0.1 监听模式"
  fi

  local has_bg_ampersand=0
  if has_background_ampersand; then
    has_bg_ampersand=1
  fi
  local has_wait_hold=0
  if has_wait_or_foreground_hold; then
    has_wait_hold=1
  fi
  if [[ $has_bg_ampersand -eq 1 && $REAL_EXEC -eq 0 && $has_wait_hold -eq 0 ]]; then
    log_result ERROR "检测到后台 '&' 启动且脚本无前台阻塞主进程。修复：追加 exec 前台主服务或 wait。"
  fi

  local start_ports=()
  while IFS= read -r line; do
    [[ -n "$line" ]] && start_ports+=("$line")
  done < <(extract_start_cmd_ports)

  local docker_ports=()
  while IFS= read -r line; do
    [[ -n "$line" ]] && docker_ports+=("$line")
  done < <(parse_docker_expose_ports)

  if [[ ${#start_ports[@]} -gt 0 ]]; then
    local sp
    for sp in "${start_ports[@]}"; do
      local found_in_docker=0
      local dp
      for dp in "${docker_ports[@]}"; do
        if [[ "$sp" == "$dp" ]]; then
          found_in_docker=1
          break
        fi
      done
      if [[ $found_in_docker -eq 0 ]]; then
        log_result WARN "启动命令显式端口 ${sp} 未在 Dockerfile EXPOSE 中声明。建议补齐 EXPOSE ${sp}。"
      fi
    done
  fi

  if [[ "$stack_hint" == "pwn" ]]; then
    local configured_start_cmd="${START_CMD_CFG:-}"

    if contains_re "$START_SH" 'exec[[:space:]]+.*xinetd[[:space:]]+.*-dontfork'; then
      log_result INFO "Pwn 场景已使用 xinetd 前台模式（exec ... -dontfork）"
    elif contains_re "$START_SH" 'exec[[:space:]]+.*tcpserver'; then
      log_result INFO "Pwn 场景已使用 tcpserver 前台模式"
    elif contains_re "$START_SH" 'exec[[:space:]]+.*socat'; then
      log_result INFO "Pwn 场景已使用 socat 前台模式"
    else
      log_result ERROR "Pwn 场景未检测到 xinetd/tcpserver/socat 前台启动。修复：使用 exec /usr/sbin/xinetd -dontfork、exec tcpserver ... 或 exec socat ...。"
    fi

    if [[ ${#docker_ports[@]} -eq 0 ]]; then
      log_result ERROR "Pwn 场景未检测到 EXPOSE 端口。修复：添加 EXPOSE <pwn_port>。"
    else
      log_result INFO "Pwn 场景 EXPOSE 端口已声明: ${docker_ports[*]}"
    fi

    local xport
    xport="$(extract_xinetd_port_from_context)"
    if [[ -n "$xport" ]]; then
      local found=0
      local p
      for p in "${docker_ports[@]}"; do
        if [[ "$p" == "$xport" ]]; then
          found=1
          break
        fi
      done
      if [[ $found -eq 1 ]]; then
        log_result INFO "Pwn 场景 EXPOSE 与 ctf.xinetd 端口一致（${xport}）"
      else
        log_result ERROR "ctf.xinetd 端口 ${xport} 未在 EXPOSE 中声明。修复：补充 EXPOSE ${xport}。"
      fi
    else
      local prefer_socat=0
      local prefer_tcpserver=0
      if [[ "${configured_start_cmd}" == *"socat"* ]]; then
        prefer_socat=1
      elif [[ "${configured_start_cmd}" == *"tcpserver"* ]]; then
        prefer_tcpserver=1
      fi

      local sport
      local tport
      sport="$(extract_socat_port_from_start)"
      tport="$(extract_tcpserver_port_from_start)"

      if [[ $prefer_socat -eq 1 && -n "$sport" ]]; then
        local sfound=0
        local sp
        for sp in "${docker_ports[@]}"; do
          if [[ "$sp" == "$sport" ]]; then
            sfound=1
            break
          fi
        done
        if [[ $sfound -eq 1 ]]; then
          log_result INFO "Pwn 场景 EXPOSE 与 socat 监听端口一致（${sport}）"
        else
          log_result ERROR "socat 监听端口 ${sport} 未在 EXPOSE 中声明。修复：补充 EXPOSE ${sport}。"
        fi
      elif [[ $prefer_tcpserver -eq 1 && -n "$tport" ]]; then
        local tfound=0
        local tp
        for tp in "${docker_ports[@]}"; do
          if [[ "$tp" == "$tport" ]]; then
            tfound=1
            break
          fi
        done
        if [[ $tfound -eq 1 ]]; then
          log_result INFO "Pwn 场景 EXPOSE 与 tcpserver 端口一致（${tport}）"
        else
          log_result ERROR "tcpserver 端口 ${tport} 未在 EXPOSE 中声明。修复：补充 EXPOSE ${tport}。"
        fi
      elif [[ -n "$tport" ]]; then
        local tfound=0
        local tp
        for tp in "${docker_ports[@]}"; do
          if [[ "$tp" == "$tport" ]]; then
            tfound=1
            break
          fi
        done
        if [[ $tfound -eq 1 ]]; then
          log_result INFO "Pwn 场景 EXPOSE 与 tcpserver 端口一致（${tport}）"
        else
          log_result ERROR "tcpserver 端口 ${tport} 未在 EXPOSE 中声明。修复：补充 EXPOSE ${tport}。"
        fi
      elif [[ -n "$sport" ]]; then
        local sfound=0
        local sp
        for sp in "${docker_ports[@]}"; do
          if [[ "$sp" == "$sport" ]]; then
            sfound=1
            break
          fi
        done
        if [[ $sfound -eq 1 ]]; then
          log_result INFO "Pwn 场景 EXPOSE 与 socat 监听端口一致（${sport}）"
        else
          log_result ERROR "socat 监听端口 ${sport} 未在 EXPOSE 中声明。修复：补充 EXPOSE ${sport}。"
        fi
      fi
    fi
  fi

  if [[ "$stack_hint" == "linux-qemu" ]]; then
    if contains_re "$START_SH" 'exec[[:space:]]+.*qemu-system-' \
      || contains_re "$START_SH" 'exec[[:space:]]+"\$\{QEMU_BINARY\}"'; then
      log_result INFO "linux-qemu 已使用 exec 启动 qemu-system-*"
    else
      log_result ERROR "linux-qemu 未检测到 exec qemu-system-* 前台启动。"
    fi

    if contains_re "$DOCKERFILE" 'qemu-system-x86|qemu-system-arm|qemu-system-[A-Za-z0-9_-]+'; then
      log_result INFO "Dockerfile 已安装或声明 QEMU system 依赖"
    else
      log_result ERROR "linux-qemu Dockerfile 未检测到 qemu-system-* 依赖。"
    fi

    local qemu_binary_cfg
    local qemu_pkg_required
    qemu_binary_cfg="$(extract_qemu_binary_from_start)"
    qemu_pkg_required="$(qemu_package_for_binary "$qemu_binary_cfg")"
    if [[ -z "$qemu_binary_cfg" ]]; then
      log_result ERROR "linux-qemu 未检测到 QEMU_BINARY 配置。"
    elif [[ -z "$qemu_pkg_required" ]]; then
      log_result WARN "未内置 ${qemu_binary_cfg} 的 Debian 包名映射，请人工确认 Dockerfile 已安装该 binary。"
    elif contains_re "$DOCKERFILE" "$qemu_pkg_required"; then
      log_result INFO "QEMU binary ${qemu_binary_cfg} 对应依赖 ${qemu_pkg_required} 已声明"
    else
      log_result ERROR "QEMU binary ${qemu_binary_cfg} 需要 ${qemu_pkg_required}，但 Dockerfile 未声明。"
    fi

    if contains_re "$START_SH" '(^|[[:space:]])-nographic([[:space:]]|$)'; then
      log_result INFO "QEMU 使用 -nographic，适合平台日志输出"
    else
      log_result ERROR "linux-qemu start.sh 未检测到 -nographic。"
    fi

    if contains_re "$START_SH" 'hostfwd=udp::[0-9]+-:[0-9]+'; then
      log_result ERROR "linux-qemu 当前版本仅支持 TCP hostfwd（自 v2.1.0 起），不支持 UDP。"
    fi

    if contains_re "$START_SH" 'hostfwd=tcp::[0-9]+-:[0-9]+'; then
      log_result INFO "QEMU user networking 已声明 hostfwd"
    else
      log_result ERROR "linux-qemu 未检测到 QEMU hostfwd，平台端口无法到达 guest 服务。"
    fi

    if contains_re "$START_SH" '(-monitor[[:space:]]+tcp:|-serial[[:space:]]+tcp:|-gdb[[:space:]]+tcp:|(^|[[:space:]])-s([[:space:]]|$)|(^|[[:space:]])-S([[:space:]]|$))'; then
      log_result ERROR "linux-qemu 检测到默认开放 monitor/gdbstub/暂停调试参数，正式交付不得默认启用。"
    elif contains_re "$START_SH" '-monitor[[:space:]]+"?none"?'; then
      log_result INFO "QEMU monitor 默认关闭"
    else
      log_result WARN "未明确检测到 -monitor none，建议关闭 QEMU monitor。"
    fi

    local qemu_base_dir
    qemu_base_dir="$(cd "$(dirname "$DOCKERFILE")" && pwd)"
    if [[ "$VM_ASSET_MODE_CFG" == "build-script" ]]; then
      if [[ -f "${qemu_base_dir}/scripts/build-vm.sh" ]]; then
        log_result INFO "linux-qemu build-script 模式检测到 scripts/build-vm.sh"
      else
        log_result ERROR "linux-qemu asset_mode=build-script 但缺少 scripts/build-vm.sh。"
      fi
    else
      local asset_missing=0
      local asset
      for asset in "$VM_KERNEL_CFG" "$VM_INITRD_CFG" "$VM_ROOTFS_CFG"; do
        if [[ -f "${qemu_base_dir}/${asset}" ]]; then
          log_result INFO "VM 资产存在: ${asset}"
        else
          log_result ERROR "VM 资产不存在: ${asset}"
          asset_missing=1
        fi
      done
      if [[ $asset_missing -eq 0 ]]; then
        log_result INFO "linux-qemu 预置 VM 资产检查通过"
      fi
    fi

    if [[ "$VM_REQUIRE_KVM_CFG" == "true" || "$VM_ACCELERATOR_CFG" == "kvm" ]]; then
      if [[ -e /dev/kvm && -r /dev/kvm && -w /dev/kvm ]]; then
        log_result INFO "KVM 配置需要 /dev/kvm，当前环境可访问"
      else
        log_result ERROR "linux-qemu 配置需要 KVM，但当前环境 /dev/kvm 不可读写。"
      fi
    elif [[ "$VM_ACCELERATOR_CFG" == "auto" ]]; then
      log_result WARN "linux-qemu accelerator=auto：交付前需记录实际使用 kvm 还是 tcg。"
    else
      log_result INFO "linux-qemu 默认使用 TCG，不要求 /dev/kvm"
    fi

    if [[ "$VM_FLAG_INJECTION_CFG" == "debugfs" ]]; then
      local changeflag_host
      changeflag_host="${qemu_base_dir}/changeflag.sh"
      if contains_re "$DOCKERFILE" 'e2fsprogs' \
        && contains_re "$START_SH" '/changeflag\.sh' \
        && [[ -f "$changeflag_host" ]] \
        && contains_re "$changeflag_host" 'debugfs[[:space:]]+-w' \
        && contains_re "$changeflag_host" '(^|[[:space:]])(write|rm|set_inode_field|sif)[[:space:]]+'; then
        log_result INFO "linux-qemu flag 注入声明为 debugfs，镜像包含 e2fsprogs，changeflag.sh 会写 guest rootfs"
      else
        log_result ERROR "linux-qemu flag_injection=debugfs 但未检测到 e2fsprogs、/changeflag.sh 调用或 debugfs 写 guest rootfs 逻辑。"
      fi
      if [[ "$VM_GUEST_FLAG_PATH_CFG" == /* ]]; then
        log_result INFO "guest flag 路径为绝对路径: ${VM_GUEST_FLAG_PATH_CFG}"
      else
        log_result ERROR "challenge.vm.guest_flag_path 必须是 guest 内绝对路径。"
      fi
    fi

    local hostfwd_ports=()
    while IFS= read -r line; do
      [[ -n "$line" ]] && hostfwd_ports+=("$line")
    done < <(
      if [[ -n "$VM_HOSTFWD_PORTS_CFG" ]]; then
        csv_to_lines "$VM_HOSTFWD_PORTS_CFG"
      else
        parse_qemu_hostfwd_ports
      fi
    )

    local fp
    for fp in "${hostfwd_ports[@]}"; do
      local found_fwd=0
      local dp
      for dp in "${docker_ports[@]}"; do
        if [[ "$fp" == "$dp" ]]; then
          found_fwd=1
          break
        fi
      done
      if [[ $found_fwd -eq 1 ]]; then
        log_result INFO "QEMU hostfwd 端口 ${fp} 已在 EXPOSE 中声明"
      else
        log_result ERROR "QEMU hostfwd 端口 ${fp} 未在 Dockerfile EXPOSE 中声明。"
      fi
    done
  fi

  if [[ "$stack_hint" == "ai" ]]; then
    if contains_re "$DOCKERFILE" 'OPENBLAS_NUM_THREADS|OMP_NUM_THREADS|MKL_NUM_THREADS|NUMEXPR_NUM_THREADS|GOTO_NUM_THREADS' \
      || contains_re "$START_SH" 'OPENBLAS_NUM_THREADS|OMP_NUM_THREADS|MKL_NUM_THREADS|NUMEXPR_NUM_THREADS|GOTO_NUM_THREADS'; then
      log_result INFO "AI 场景已设置线程限制变量"
    else
      log_result WARN "AI 场景未检测到线程限制变量。建议设置 OPENBLAS/OMP/MKL/NUMEXPR/GOTO 线程为 1。"
    fi

    if contains_re "$START_SH" 'gunicorn[[:space:]]+.*-b[[:space:]]+0\.0\.0\.0'; then
      log_result INFO "AI 场景已使用 gunicorn 前台监听 0.0.0.0"
    else
      log_result WARN "AI 场景建议使用 gunicorn 前台并监听 0.0.0.0。示例：gunicorn -w 1 --threads 1 -b 0.0.0.0:5000 app:app。"
    fi
  fi

  if [[ "$PROFILE_CFG" != "jeopardy" || "$stack_hint" == "rdg" || "$stack_hint" == "secops" ]]; then
    local rdg_user_re
    rdg_user_re="$(escape_regex "$RDG_CTF_USER_CFG")"

    if [[ "$RDG_ENABLE_TTYD_CFG" == "true" ]]; then
      if contains_re "$DOCKERFILE" '/ttyd' && contains_re "$DOCKERFILE" 'chmod[[:space:]]+.*(/ttyd)'; then
        log_result INFO "Defense 场景检测到 /ttyd 产物落地与赋权逻辑"
      else
        log_result ERROR "profile=${PROFILE_CFG} enable_ttyd=true 但未检测到 /ttyd 构建逻辑。修复：将 ttyd 复制到 /ttyd 并 chmod 755。"
      fi

      if contains_re "$START_SH" '(^|[^A-Za-z0-9_/-])/ttyd([^A-Za-z0-9_/-]|$)|ttyd'; then
        log_result INFO "Defense 场景检测到 ttyd 启动逻辑"
      else
        log_result ERROR "profile=${PROFILE_CFG} enable_ttyd=true 但 start.sh 未检测到 ttyd 启动逻辑。"
      fi

      if [[ "$RDG_TTYD_INSTALL_FALLBACK_CFG" == "true" ]]; then
        if contains_re "$DOCKERFILE" '(apt-get[[:space:]].*ttyd|apk[[:space:]]+add.*ttyd)'; then
          log_result INFO "Defense 场景检测到 ttyd 安装回退逻辑"
        else
          log_result ERROR "profile=${PROFILE_CFG} ttyd_install_fallback=true 但未检测到 ttyd 安装回退逻辑。"
        fi
      fi
    else
      log_result INFO "profile=${PROFILE_CFG} enable_ttyd=false：跳过 ttyd 强制校验"
    fi

    if [[ "$RDG_ENABLE_SSHD_CFG" == "true" ]]; then
      if contains_re "$DOCKERFILE" '(openssh|sshd|ssh-keygen)'; then
        log_result INFO "Defense 场景检测到 sshd 安装/配置逻辑"
      else
        log_result ERROR "profile=${PROFILE_CFG} enable_sshd=true 但未检测到 sshd 安装或配置逻辑。"
      fi

      if contains_re "$START_SH" '(/usr/sbin/sshd|(^|[[:space:]])sshd)([[:space:]]|$)'; then
        log_result INFO "Defense 场景检测到 sshd 启动逻辑"
      else
        log_result ERROR "profile=${PROFILE_CFG} enable_sshd=true 但 start.sh 未检测到 sshd 启动逻辑。"
      fi
    else
      log_result INFO "profile=${PROFILE_CFG} enable_sshd=false：跳过 sshd 强制校验"
    fi

    if contains_re "$DOCKERFILE" "(useradd|adduser)[[:space:]].*${rdg_user_re}" \
      || (contains_re "$DOCKERFILE" '(useradd|adduser)' && contains_re "$DOCKERFILE" 'CTF_USER'); then
      log_result INFO "Defense 场景检测到 ctf 用户创建逻辑"
    else
      log_result ERROR "Defense 场景未检测到 ctf 用户创建。修复：创建 ${RDG_CTF_USER_CFG} 账号。"
    fi

    if contains_re "$DOCKERFILE" '(chpasswd|passwd[[:space:]])' || contains_re "$START_SH" '(chpasswd|passwd[[:space:]])'; then
      log_result INFO "Defense 场景检测到 ctf 用户密码初始化逻辑"
    else
      log_result ERROR "Defense 场景未检测到 ctf 用户密码初始化。修复：设置默认口令（例如 123456）。"
    fi

    if [[ "$RDG_CTF_IN_ROOT_GROUP_CFG" == "true" ]]; then
      if contains_re "$DOCKERFILE" "(usermod[[:space:]]+-aG[[:space:]]+root[[:space:]]+${rdg_user_re}|addgroup[[:space:]]+${rdg_user_re}[[:space:]]+root)" \
        || (contains_re "$DOCKERFILE" '(usermod[[:space:]]+-aG[[:space:]]+root|addgroup[[:space:]].*[[:space:]]+root)' && contains_re "$DOCKERFILE" 'CTF_USER'); then
        log_result INFO "Defense 场景检测到 ctf 用户加入 root 组逻辑"
      else
        log_result ERROR "profile=${PROFILE_CFG} ctf_in_root_group=true 但未检测到加组逻辑。"
      fi
    fi

    if contains_re "$DOCKERFILE" '^[[:space:]]*EXPOSE[[:space:]]+[0-9]+'; then
      log_result INFO "Defense 场景已声明 EXPOSE 端口"
    else
      log_result ERROR "profile=${PROFILE_CFG} 未检测到 EXPOSE 端口声明。"
    fi

    if is_multiservice_start; then
      log_result INFO "Defense 场景检测到多服务启动模式"
    else
      log_result WARN "Defense 场景未检测到多服务启动模式，可按题目需求保持单服务。"
    fi

    if [[ "$RDG_SCORING_MODE_CFG" == "check_service" && "$RDG_CHECK_ENABLED_CFG" == "true" ]]; then
      local base_dir
      base_dir="$(cd "$(dirname "$DOCKERFILE")" && pwd)"
      local check_rel
      local check_candidate
      check_rel="$RDG_CHECK_SCRIPT_PATH_CFG"
      if [[ "$check_rel" == /* ]]; then
        if [[ -n "$RDG_WORKDIR_CFG" && "$check_rel" == "${RDG_WORKDIR_CFG%/}/"* ]]; then
          check_rel="${check_rel#${RDG_WORKDIR_CFG%/}/}"
        else
          check_rel="${check_rel#/}"
        fi
      fi
      check_candidate="${base_dir}/${check_rel}"
      if [[ -f "$check_candidate" ]]; then
        log_result INFO "check_service 脚本存在：${check_rel}"
        local check_line_count
        check_line_count="$(grep -cv '^[[:space:]]*$' "$check_candidate" || true)"

        if contains_re "$check_candidate" '(CHECK_IMPLEMENT_ME|CHECK_REVIEW_REQUIRED|TODO[[:space:]]*implement|TODO:|placeholder)'; then
          log_result ERROR "check_service 脚本仍为占位实现：${check_rel}。修复：按真实业务补齐健康检查与漏洞负向检查逻辑。"
        elif [[ "${check_line_count}" -le 8 ]] && contains_re "$check_candidate" 'exit[[:space:]]+0([[:space:]]|$)'; then
          log_result ERROR "check_service 脚本疑似占位实现（脚本过短且直接 exit 0）：${check_rel}。"
        else
          log_result INFO "check_service 脚本通过占位检测"
        fi
      else
        log_result ERROR "scoring_mode=check_service 但缺少校验脚本：${check_rel}"
      fi
    fi

    if [[ "$PROFILE_CFG" == "awdp" ]]; then
      local base_dir
      base_dir="$(cd "$(dirname "$DOCKERFILE")" && pwd)"
      if [[ -d "${base_dir}/patch/src" ]]; then
        log_result INFO "AWDP 检测到 patch/src 目录"
      else
        log_result ERROR "AWDP 缺少 patch/src 目录。"
      fi
      if [[ -x "${base_dir}/patch/patch.sh" ]]; then
        log_result INFO "AWDP 检测到 patch/patch.sh"
      else
        log_result ERROR "AWDP 缺少可执行 patch/patch.sh。"
      fi
      if [[ -f "${base_dir}/patch_bundle.tar.gz" ]]; then
        log_result INFO "AWDP 检测到 patch_bundle.tar.gz"
      else
        log_result ERROR "AWDP 缺少 patch_bundle.tar.gz。修复：重新渲染或打包补丁产物。"
      fi
    fi
  fi
}

run_challenge_port_check() {
  if [[ -z "$CHALLENGE_YAML" ]]; then
    return
  fi

  echo
  echo "[E] challenge.yaml 端口一致性"

  if [[ ! -f "$CHALLENGE_YAML" ]]; then
    log_result WARN "challenge.yaml 不存在，跳过端口一致性校验: $CHALLENGE_YAML"
    return
  fi

  expected_ports=()
  docker_ports=()

  while IFS= read -r line; do
    [[ -n "$line" ]] && expected_ports+=("$line")
  done < <(parse_challenge_ports "$CHALLENGE_YAML")

  while IFS= read -r line; do
    [[ -n "$line" ]] && docker_ports+=("$line")
  done < <(parse_docker_expose_ports)

  if [[ ${#expected_ports[@]} -eq 0 ]]; then
    log_result WARN "challenge.yaml 未解析到 expose_ports，跳过端口一致性校验"
    return
  fi

  missing_ports=()
  for p in "${expected_ports[@]}"; do
    found=0
    for dp in "${docker_ports[@]}"; do
      if [[ "$p" == "$dp" ]]; then
        found=1
        break
      fi
    done
    if [[ $found -eq 0 ]]; then
      missing_ports+=("$p")
    fi
  done

  if [[ ${#missing_ports[@]} -eq 0 ]]; then
    log_result INFO "EXPOSE 端口与 challenge.yaml 一致"
  else
    log_result ERROR "EXPOSE 缺少 challenge.yaml 声明端口: ${missing_ports[*]}。修复：补充 EXPOSE ${missing_ports[*]}。"
  fi

  local start_ports=()
  while IFS= read -r line; do
    [[ -n "$line" ]] && start_ports+=("$line")
  done < <(extract_start_cmd_ports)

  if [[ ${#start_ports[@]} -gt 0 ]]; then
    local sp
    for sp in "${start_ports[@]}"; do
      local found=0
      local ep
      for ep in "${expected_ports[@]}"; do
        if [[ "$sp" == "$ep" ]]; then
          found=1
          break
        fi
      done
      if [[ $found -eq 0 ]]; then
        log_result WARN "启动命令显式端口 ${sp} 未在 challenge.expose_ports 声明。建议同步 challenge.yaml。"
      fi
    done
  fi
}

echo "开始校验"
echo "- Dockerfile: $DOCKERFILE"
echo "- start.sh:   $START_SH"
if [[ -n "$CHALLENGE_YAML" ]]; then
  echo "- challenge:  $CHALLENGE_YAML"
fi
echo "- verification: ${VALIDATION_LAYER}"

echo

if ! load_rdg_config_from_challenge; then
  echo
  echo "校验汇总"
  echo "- 总检查项: $CHECK_COUNT"
  echo "- ERROR:    $ERROR_COUNT"
  echo "- WARN:     $WARN_COUNT"
  echo "- INFO:     $INFO_COUNT"
  echo "结果：失败（challenge.yaml 上下文解析失败）"
  write_json_summary 2 "CONFIG_CONTEXT_PARSE_FAILED" "challenge.yaml 上下文解析失败"
  exit 2
fi

run_hard_rules
run_configurable_rules
if [[ "$DYNAMIC_FLAG_CHECK" == "true" ]]; then
  run_dynamic_checks
else
  echo
  echo "[D] 动态策略检查"
  log_result INFO "已按 --static-only 跳过动态 flag 写入检查"
fi
run_challenge_port_check

echo
echo "校验汇总"
echo "- 总检查项: $CHECK_COUNT"
echo "- ERROR:    $ERROR_COUNT"
echo "- WARN:     $WARN_COUNT"
echo "- INFO:     $INFO_COUNT"

if [[ $ERROR_COUNT -gt 0 ]]; then
  echo "结果：失败（存在 ERROR）"
  write_json_summary 1 "CONTRACT_VALIDATION_FAILED" "存在 ERROR"
  exit 1
fi

echo "结果：通过（无 ERROR）"
write_json_summary 0 "CONTRACT_VALIDATION_PASSED" "无 ERROR"
exit 0
