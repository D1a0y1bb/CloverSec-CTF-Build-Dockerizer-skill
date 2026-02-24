#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
用法：
  bash scripts/validate.sh Dockerfile start.sh [challenge.yaml]

说明：
  - 先执行平台硬规则，再执行 data/validate_rules.yaml 可配置规则。
  - 输出分级检查结果：ERROR/WARN/INFO
  - 有 ERROR 时退出码为 1；否则退出 0
USAGE
}

if [[ ${1:-} == "-h" || ${1:-} == "--help" ]]; then
  usage
  exit 0
fi

if [[ $# -lt 2 || $# -gt 3 ]]; then
  usage
  exit 2
fi

DOCKERFILE="$1"
START_SH="$2"
CHALLENGE_YAML="${3:-}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
RULES_FILE="${SKILL_ROOT}/data/validate_rules.yaml"

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
  if [[ ${#parts[@]} -ge 2 ]]; then
    echo "${parts[1]}"
  else
    echo ""
  fi
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

  if contains_re "$START_SH" 'xinetd|ctf\.xinetd' || contains_re "$DOCKERFILE" 'xinetd'; then
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

  if contains_re "$DOCKERFILE" '^[[:space:]]*(COPY|ADD)[[:space:]].*start\.sh.*(/start\.sh|"/start\.sh")'; then
    log_result INFO "Dockerfile 已将 start.sh 放置到 /start.sh"
  else
    log_result ERROR "未检测到 /start.sh 拷贝逻辑。修复：在 Dockerfile 增加 `COPY start.sh /start.sh`。"
  fi

  if contains_re "$DOCKERFILE" '^[[:space:]]*(COPY|ADD)[[:space:]].*flag.*(/flag|"/flag")' \
    || contains_re "$DOCKERFILE" '^[[:space:]]*RUN[[:space:]].*(touch|echo|printf|install).*([[:space:]]|>)\/flag'; then
    log_result INFO "Dockerfile 已创建或复制 /flag"
  else
    log_result ERROR "未检测到 /flag 创建逻辑。修复：增加 `COPY flag /flag` 或 `RUN touch /flag`。"
  fi

  if contains_re "$DOCKERFILE" 'chmod.*(\+x|a\+x|u\+x|555|755|775).*/start\.sh'; then
    log_result INFO "Dockerfile 已对 /start.sh 设置可执行权限"
  else
    log_result ERROR "未检测到 /start.sh 可执行权限。修复：增加 `RUN chmod 555 /start.sh`。"
  fi

  if contains_re "$DOCKERFILE" 'chmod.*(444|644|664|744|755|a\+r|u\+r|go\+r).*/flag'; then
    log_result INFO "Dockerfile 已对 /flag 设置可读权限"
  else
    log_result ERROR "未检测到 /flag 可读权限。修复：增加 `RUN chmod 444 /flag`。"
  fi

  FIRST_LINE="$(head -n1 "$START_SH" | tr -d '\r')"
  if [[ "$FIRST_LINE" == "#!/bin/bash" ]]; then
    log_result INFO "start.sh 首行是 #!/bin/bash"
  else
    log_result ERROR "start.sh 首行必须是 #!/bin/bash。修复：将 shebang 改为 `#!/bin/bash`。"
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
        log_result ERROR "WORKDIR 与 start.sh 路径不一致。修复：在 start.sh 增加 `cd ${WORKDIR_VALUE}`。"
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
      log_result ERROR "单服务未使用 exec 启动主进程。修复：将启动行改为 `exec <主命令>`。"
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

  if [[ "$stack_hint" == "pwn" ]]; then
    if contains_re "$START_SH" 'exec[[:space:]]+.*xinetd[[:space:]]+.*-dontfork'; then
      log_result INFO "Pwn 场景已使用 xinetd 前台模式（exec ... -dontfork）"
    else
      log_result ERROR "Pwn 场景未检测到 xinetd 前台启动。修复：在 start.sh 使用 `exec /usr/sbin/xinetd -dontfork`。"
    fi

    local docker_ports=()
    while IFS= read -r line; do
      [[ -n "$line" ]] && docker_ports+=("$line")
    done < <(parse_docker_expose_ports)
    if [[ ${#docker_ports[@]} -eq 0 ]]; then
      log_result ERROR "Pwn 场景未检测到 EXPOSE 端口。修复：添加 `EXPOSE <pwn_port>`。"
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
        log_result ERROR "ctf.xinetd 端口 ${xport} 未在 EXPOSE 中声明。修复：补充 `EXPOSE ${xport}`。"
      fi
    fi
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
      log_result WARN "AI 场景建议使用 gunicorn 前台并监听 0.0.0.0。示例：`gunicorn -w 1 --threads 1 -b 0.0.0.0:5000 app:app`。"
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
    log_result ERROR "EXPOSE 缺少 challenge.yaml 声明端口: ${missing_ports[*]}。修复：补充 `EXPOSE ${missing_ports[*]}`。"
  fi
}

echo "开始校验"
echo "- Dockerfile: $DOCKERFILE"
echo "- start.sh:   $START_SH"
if [[ -n "$CHALLENGE_YAML" ]]; then
  echo "- challenge:  $CHALLENGE_YAML"
fi

echo

run_hard_rules
run_configurable_rules
run_dynamic_checks
run_challenge_port_check

echo
echo "校验汇总"
echo "- 总检查项: $CHECK_COUNT"
echo "- ERROR:    $ERROR_COUNT"
echo "- WARN:     $WARN_COUNT"
echo "- INFO:     $INFO_COUNT"

if [[ $ERROR_COUNT -gt 0 ]]; then
  echo "结果：失败（存在 ERROR）"
  exit 1
fi

echo "结果：通过（无 ERROR）"
exit 0
