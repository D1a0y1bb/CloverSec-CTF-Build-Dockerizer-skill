#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
EXAMPLES_DIR="${SKILL_ROOT}/examples"
RENDER_PY="${SCRIPT_DIR}/render.py"
RENDER_SCENARIO_PY="${SCRIPT_DIR}/render_scenario.py"
VALIDATE_SH="${SCRIPT_DIR}/validate.sh"
VALIDATE_SCENARIO_PY="${SCRIPT_DIR}/validate_scenario.py"

FULL_RUN="${SMOKE_FULL_RUN:-0}"
FORCE_RUN_LIST="${SMOKE_FORCE_RUN:-node-basic,php-apache-basic,python-flask-basic,pwn-basic,ai-basic,rdg-php-hardening-basic,rdg-python-ssti-basic,baseunit-redis-basic,baseunit-sshd-basic,node-awdp-basic,secops-nginx-basic,secops-redis-hardening-basic}"
WAIT_SECONDS="${SMOKE_WAIT_SECONDS:-5}"
KEEP_ARTIFACTS="${KEEP_SMOKE_ARTIFACTS:-0}"
LAMP_RUN_MODE="${LAMP_RUN_MODE:-build-only}" # build-only/full
AI_TRANSFORMERS_RUN_MODE="${AI_TRANSFORMERS_RUN_MODE:-build-only}" # build-only/full

PASS_LIST=()
FAIL_LIST=()
SKIP_LIST=()

if ! command -v docker >/dev/null 2>&1; then
  echo "[ERROR] 未检测到 docker 命令，无法执行冒烟测试。" >&2
  exit 2
fi

if ! docker info >/dev/null 2>&1; then
  echo "[ERROR] docker daemon 不可访问（可能是权限或服务未启动）。" >&2
  exit 2
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "[ERROR] 未检测到 python3，无法执行 render.py。" >&2
  exit 2
fi

if ! python3 - <<'PY' >/dev/null 2>&1
import yaml  # noqa: F401
PY
then
  echo "[ERROR] 缺少 PyYAML（python3 模块 yaml），无法执行冒烟测试。" >&2
  echo "[ERROR] 请先安装: pip3 install -r ${SCRIPT_DIR}/requirements.txt" >&2
  exit 2
fi

if [[ ! -d "$EXAMPLES_DIR" ]]; then
  echo "[ERROR] examples 目录不存在: $EXAMPLES_DIR" >&2
  exit 2
fi

contains_csv_item() {
  local needle="$1"
  local csv="$2"
  local item
  IFS=',' read -r -a arr <<< "$csv"
  for item in "${arr[@]}"; do
    if [[ "${item}" == "${needle}" ]]; then
      return 0
    fi
  done
  return 1
}

get_first_port() {
  local challenge_file="$1"
  python3 - "$challenge_file" <<'PY'
import sys
from pathlib import Path

path = Path(sys.argv[1])
if not path.exists():
    print("80")
    raise SystemExit(0)

import yaml

raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
challenge = raw.get("challenge", {}) if isinstance(raw, dict) else {}
ports = challenge.get("expose_ports", []) if isinstance(challenge, dict) else []

if isinstance(ports, list) and ports:
    p = str(ports[0]).strip()
    print(p if p else "80")
elif isinstance(ports, str) and ports.strip():
    print(ports.strip().split()[0])
else:
    print("80")
PY
}

get_stack_id() {
  local challenge_file="$1"
  python3 - "$challenge_file" <<'PY'
import sys
from pathlib import Path

path = Path(sys.argv[1])
if not path.exists():
    print("")
    raise SystemExit(0)

import yaml

raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
challenge = raw.get("challenge", {}) if isinstance(raw, dict) else {}
stack = challenge.get("stack", "") if isinstance(challenge, dict) else ""
print(str(stack).strip().lower())
PY
}

get_profile_id() {
  local challenge_file="$1"
  python3 - "$challenge_file" <<'PY'
import sys
from pathlib import Path

path = Path(sys.argv[1])
if not path.exists():
    print("")
    raise SystemExit(0)

import yaml

raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
challenge = raw.get("challenge", {}) if isinstance(raw, dict) else {}
profile = challenge.get("profile", "") if isinstance(challenge, dict) else ""
print(str(profile).strip().lower())
PY
}

get_check_contract() {
  local challenge_file="$1"
  python3 - "$challenge_file" <<'PY'
import sys
from pathlib import Path

path = Path(sys.argv[1])
if not path.exists():
    print("false|flag|check/check.sh")
    raise SystemExit(0)

import yaml

raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
challenge = raw.get("challenge", {}) if isinstance(raw, dict) else {}
if not isinstance(challenge, dict):
    print("false|flag|check/check.sh")
    raise SystemExit(0)

cfg = challenge.get("defense")
if not isinstance(cfg, dict):
    cfg = challenge.get("rdg")
if not isinstance(cfg, dict):
    cfg = {}

enabled = bool(cfg.get("check_enabled", False))
mode = str(cfg.get("scoring_mode", "flag")).strip().lower() or "flag"
path_value = str(cfg.get("check_script_path", "check/check.sh")).strip() or "check/check.sh"
print(f"{str(enabled).lower()}|{mode}|{path_value}")
PY
}

cleanup_case() {
  local cname="$1"
  local image_tag="$2"

  if [[ "$KEEP_ARTIFACTS" == "1" ]]; then
    return
  fi

  docker rm -f "$cname" >/dev/null 2>&1 || true
  docker rmi "$image_tag" >/dev/null 2>&1 || true
}

should_run_container() {
  local example_name="$1"

  if [[ "$FULL_RUN" == "1" ]]; then
    if [[ "$example_name" == *"lamp"* && "$LAMP_RUN_MODE" != "full" ]]; then
      return 1
    fi
    if [[ "$example_name" == "ai-transformers-basic" && "$AI_TRANSFORMERS_RUN_MODE" != "full" ]]; then
      return 1
    fi
    return 0
  fi

  if [[ "$example_name" == *"lamp"* && "$LAMP_RUN_MODE" != "full" ]]; then
    return 1
  fi

  if [[ "$example_name" == "ai-transformers-basic" && "$AI_TRANSFORMERS_RUN_MODE" != "full" ]]; then
    return 1
  fi

  if contains_csv_item "$example_name" "$FORCE_RUN_LIST"; then
    return 0
  fi

  return 1
}

echo "开始冒烟测试（遍历 examples 全目录）"
echo "- FULL_RUN: ${FULL_RUN}"
echo "- FORCE_RUN: ${FORCE_RUN_LIST}"
echo "- LAMP_RUN_MODE: ${LAMP_RUN_MODE}"
echo "- AI_TRANSFORMERS_RUN_MODE: ${AI_TRANSFORMERS_RUN_MODE}"
echo "- WAIT_SECONDS: ${WAIT_SECONDS}"

while IFS= read -r dir; do
  name="$(basename "$dir")"
  challenge_yaml="${dir}/challenge.yaml"
  scenario_yaml="${dir}/scenario.yaml"
  dockerfile="${dir}/Dockerfile"
  start_sh="${dir}/start.sh"

  echo
  echo "== 测试目录: ${name} =="

  if [[ -f "$scenario_yaml" ]]; then
    scenario_out="$(mktemp -d "/tmp/ctf-scenario-${name}-XXXXXX")"
    echo "[INFO] 检测到 scenario.yaml，执行 scenario 渲染与校验"
    if ! python3 "$RENDER_SCENARIO_PY" --config "$scenario_yaml" --output "$scenario_out"; then
      echo "[ERROR] scenario render 失败: ${name}"
      FAIL_LIST+=("${name}:scenario-render")
      rm -rf "$scenario_out"
      continue
    fi

    compose_file="${scenario_out}/docker-compose.yml"
    if ! python3 "$VALIDATE_SCENARIO_PY" "$compose_file" "$scenario_out"; then
      echo "[ERROR] scenario validate 失败: ${name}"
      FAIL_LIST+=("${name}:scenario-validate")
      rm -rf "$scenario_out"
      continue
    fi

    if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
      if ! docker compose -f "$compose_file" build; then
        echo "[ERROR] docker compose build 失败: ${name}"
        FAIL_LIST+=("${name}:scenario-build")
        rm -rf "$scenario_out"
        continue
      fi
    else
      echo "[WARN] 未检测到 docker compose，scenario 仅执行静态校验: ${name}"
    fi

    PASS_LIST+=("${name}:scenario")
    rm -rf "$scenario_out"
    continue
  fi

  if [[ ! -f "$challenge_yaml" ]]; then
    echo "[WARN] 缺少 challenge.yaml，跳过: ${dir}"
    SKIP_LIST+=("${name}")
    continue
  fi

  if ! python3 "$RENDER_PY" --config "$challenge_yaml" --output "$dir"; then
    echo "[ERROR] render 失败: ${name}"
    FAIL_LIST+=("${name}:render")
    continue
  fi

  if ! bash "$VALIDATE_SH" "$dockerfile" "$start_sh" "$challenge_yaml"; then
    echo "[ERROR] validate 失败: ${name}"
    FAIL_LIST+=("${name}:validate")
    continue
  fi

  image_tag="ctf-skill-test:${name}"
  container_name="ctf-skill-test-${name}-$(date +%s)-$RANDOM"

  if ! docker build -t "$image_tag" "$dir"; then
    echo "[ERROR] docker build 失败: ${name}"
    FAIL_LIST+=("${name}:build")
    cleanup_case "$container_name" "$image_tag"
    continue
  fi

  if ! should_run_container "$name"; then
    echo "[INFO] 当前目录按策略执行 build + validate，不执行 run"
    PASS_LIST+=("${name}:build-only")
    cleanup_case "$container_name" "$image_tag"
    continue
  fi

  container_port="$(get_first_port "$challenge_yaml")"
  cid="$(docker run -d -p "0:${container_port}" --name "$container_name" "$image_tag" /start.sh || true)"

  if [[ -z "$cid" ]]; then
    echo "[ERROR] docker run 失败: ${name}"
    FAIL_LIST+=("${name}:run")
    cleanup_case "$container_name" "$image_tag"
    continue
  fi

  sleep "$WAIT_SECONDS"

  running_id="$(docker ps --filter "id=${cid}" --format '{{.ID}}')"
  logs_out="$(docker logs --tail 50 "$cid" 2>&1 || true)"

  if [[ -z "$running_id" ]]; then
    echo "[ERROR] 容器未保持运行: ${name}"
    if [[ -n "$logs_out" ]]; then
      echo "[INFO] 日志输出："
      echo "$logs_out"
    fi
    FAIL_LIST+=("${name}:not-running")
    cleanup_case "$container_name" "$image_tag"
    continue
  fi

  if [[ -z "${logs_out//[[:space:]]/}" ]]; then
    echo "[ERROR] 容器无可观测日志输出: ${name}"
    FAIL_LIST+=("${name}:no-logs")
    cleanup_case "$container_name" "$image_tag"
    continue
  fi

  echo "[INFO] 容器运行正常，日志前 50 行："
  echo "$logs_out"

  host_port="$(docker port "$cid" "${container_port}/tcp" 2>/dev/null | head -n1 | awk -F: '{print $NF}' || true)"
  if [[ -z "${host_port}" ]]; then
    echo "[WARN] 无法解析宿主端口映射: ${name} ${container_port}/tcp"
  fi

  assert_script="${dir}/smoke_assert.sh"
  if [[ -f "${assert_script}" ]]; then
    if [[ -z "${host_port}" ]]; then
      echo "[ERROR] 需要执行 smoke_assert.sh 但端口映射解析失败: ${name}"
      FAIL_LIST+=("${name}:assert-port-resolve")
      cleanup_case "$container_name" "$image_tag"
      continue
    fi
    echo "[INFO] 执行自定义断言脚本: ${assert_script}"
    if ! bash "${assert_script}" "${cid}" "${host_port}" "${container_port}"; then
      echo "[ERROR] smoke_assert.sh 失败: ${name}"
      FAIL_LIST+=("${name}:smoke-assert")
      cleanup_case "$container_name" "$image_tag"
      continue
    fi
  fi

  stack_id="$(get_stack_id "$challenge_yaml")"
  profile_id="$(get_profile_id "$challenge_yaml")"
  check_contract="$(get_check_contract "$challenge_yaml")"
  check_enabled="${check_contract%%|*}"
  check_rest="${check_contract#*|}"
  check_mode="${check_rest%%|*}"
  check_script_rel="${check_rest#*|}"
  if [[ "${check_enabled}" == "true" && "${check_mode}" == "check_service" ]]; then
    check_script="${dir}/${check_script_rel}"
    if [[ ! -f "${check_script}" ]]; then
      echo "[ERROR] check_service 示例缺少 check 脚本: ${check_script}"
      FAIL_LIST+=("${name}:missing-check-script")
      cleanup_case "$container_name" "$image_tag"
      continue
    fi

    if [[ -z "${host_port}" ]]; then
      echo "[ERROR] 无法解析 check_service 检查端口映射: ${name} ${container_port}/tcp"
      FAIL_LIST+=("${name}:check-port-resolve")
      cleanup_case "$container_name" "$image_tag"
      continue
    fi

    echo "[INFO] 执行 check 脚本: ${check_script} 127.0.0.1 ${host_port} (stack=${stack_id} profile=${profile_id})"
    if ! bash "${check_script}" "127.0.0.1" "${host_port}"; then
      echo "[ERROR] check 脚本失败: ${name}"
      FAIL_LIST+=("${name}:service-check")
      cleanup_case "$container_name" "$image_tag"
      continue
    fi
  fi

  PASS_LIST+=("${name}")
  cleanup_case "$container_name" "$image_tag"
done < <(find "$EXAMPLES_DIR" -mindepth 1 -maxdepth 1 -type d | sort)

echo
echo "冒烟测试汇总"
echo "- 通过: ${#PASS_LIST[@]}"
if [[ ${#PASS_LIST[@]} -gt 0 ]]; then
  printf '  %s\n' "${PASS_LIST[@]}"
fi

echo "- 失败: ${#FAIL_LIST[@]}"
if [[ ${#FAIL_LIST[@]} -gt 0 ]]; then
  printf '  %s\n' "${FAIL_LIST[@]}"
fi

echo "- 跳过: ${#SKIP_LIST[@]}"
if [[ ${#SKIP_LIST[@]} -gt 0 ]]; then
  printf '  %s\n' "${SKIP_LIST[@]}"
fi

if [[ ${#FAIL_LIST[@]} -gt 0 ]]; then
  exit 1
fi

exit 0
