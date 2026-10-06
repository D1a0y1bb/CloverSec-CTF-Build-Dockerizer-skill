#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
EXAMPLES_DIR="${SKILL_ROOT}/examples"
WORK_EXAMPLES_DIR="$EXAMPLES_DIR"
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
LINUX_QEMU_RUN_MODE="${LINUX_QEMU_RUN_MODE:-validate-only}" # validate-only/build-only/full
SCENARIO_VALIDATE_RENDERED="${SCENARIO_VALIDATE_RENDERED:-1}"
SKIP_DOCKER="${SKIP_DOCKER:-0}"
SMOKE_READONLY="${SMOKE_READONLY:-1}"
SMOKE_OUTPUT_ROOT="${SMOKE_OUTPUT_ROOT:-}"
SMOKE_WORK_ROOT=""
SMOKE_CASES="${SMOKE_CASES:-}"
CASE_FILTERS=()
if [[ -n "$SMOKE_CASES" ]]; then
  IFS=',' read -r -a CASE_FILTERS <<< "$SMOKE_CASES"
fi

usage() {
  cat <<'USAGE'
用法：
  bash scripts/smoke_test.sh [--case NAME] [--in-place] [--output-root DIR] [--skip-docker]

默认行为：
  复制 examples 到临时目录后执行 render/validate/build/run，不写回原 examples。

参数：
  --case NAME       只测试指定 examples 子目录，可重复传入；也可用 SMOKE_CASES=a,b
  --in-place        在原 examples 目录执行旧流程
  --output-root DIR 指定只读副本根目录
  --skip-docker     只执行 render/validate，不执行 docker build/run
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --case)
      if [[ $# -lt 2 || -z "${2:-}" ]]; then
        echo "[ERROR] --case 需要 examples 子目录名称" >&2
        exit 2
      fi
      CASE_FILTERS+=("$2")
      shift 2
      ;;
    --in-place)
      SMOKE_READONLY=0
      shift
      ;;
    --output-root)
      if [[ $# -lt 2 || -z "${2:-}" ]]; then
        echo "[ERROR] --output-root 需要目录参数" >&2
        exit 2
      fi
      SMOKE_OUTPUT_ROOT="$2"
      shift 2
      ;;
    --skip-docker)
      SKIP_DOCKER=1
      shift
      ;;
    *)
      echo "[ERROR] 未知参数: $1" >&2
      usage
      exit 2
      ;;
  esac
done

PASS_LIST=()
FAIL_LIST=()
SKIP_LIST=()

if [[ "$SKIP_DOCKER" != "1" ]]; then
  if ! command -v docker >/dev/null 2>&1; then
    echo "[ERROR] 未检测到 docker 命令，无法执行冒烟测试。" >&2
    exit 2
  fi

  if ! docker info >/dev/null 2>&1; then
    echo "[ERROR] docker daemon 不可访问（可能是权限或服务未启动）。" >&2
    exit 2
  fi
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

cleanup_work_root() {
  if [[ "$SMOKE_READONLY" == "0" || "$KEEP_ARTIFACTS" == "1" || -z "$SMOKE_WORK_ROOT" ]]; then
    return
  fi
  if [[ -z "$SMOKE_OUTPUT_ROOT" ]]; then
    rm -rf "$SMOKE_WORK_ROOT"
  fi
}

if [[ "$SMOKE_READONLY" != "0" ]]; then
  if [[ -n "$SMOKE_OUTPUT_ROOT" ]]; then
    SMOKE_WORK_ROOT="$(mkdir -p "$SMOKE_OUTPUT_ROOT" && cd "$SMOKE_OUTPUT_ROOT" && pwd)"
    rm -rf "${SMOKE_WORK_ROOT}/examples"
  else
    SMOKE_WORK_ROOT="$(mktemp -d "/tmp/ctf-smoke-examples-XXXXXX")"
  fi
  cp -R "$EXAMPLES_DIR" "${SMOKE_WORK_ROOT}/examples"
  WORK_EXAMPLES_DIR="${SMOKE_WORK_ROOT}/examples"
  trap cleanup_work_root EXIT
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

case_selected() {
  local name="$1"
  local item

  if [[ ${#CASE_FILTERS[@]} -eq 0 ]]; then
    return 0
  fi

  for item in "${CASE_FILTERS[@]}"; do
    if [[ "$item" == "$name" ]]; then
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

resolve_host_port() {
  local cid="$1"
  local container_port="$2"
  local host_port=""
  local attempt

  for attempt in {1..10}; do
    host_port="$(docker port "$cid" "${container_port}/tcp" 2>/dev/null | head -n1 | awk -F: '{print $NF}' || true)"
    if [[ -n "${host_port}" ]]; then
      printf '%s\n' "$host_port"
      return 0
    fi

    host_port="$(docker inspect "$cid" 2>/dev/null | python3 -c '
import json
import sys

container_port = sys.argv[1].split("/")[0] + "/tcp"
try:
    data = json.load(sys.stdin)
except Exception:
    raise SystemExit(0)
if not data:
    raise SystemExit(0)
ports = (((data[0] or {}).get("NetworkSettings") or {}).get("Ports") or {})
for item in ports.get(container_port) or []:
    host_port = str((item or {}).get("HostPort") or "").strip()
    if host_port:
        print(host_port)
        raise SystemExit(0)
' "$container_port" || true)"
    if [[ -n "${host_port}" ]]; then
      printf '%s\n' "$host_port"
      return 0
    fi

    sleep 0.5
  done
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

run_smoke_assert_yaml() {
  local yaml_path="$1"
  local cid="$2"
  local host_port="$3"
  local container_port="$4"
  python3 - "$yaml_path" "$cid" "$host_port" "$container_port" <<'PY'
import socket
import subprocess
import sys
import urllib.error
import urllib.request

import yaml

yaml_path, cid, host_port, _container_port = sys.argv[1:5]
with open(yaml_path, "r", encoding="utf-8") as handle:
    raw = yaml.safe_load(handle) or {}

assertions = raw.get("assertions")
if not isinstance(assertions, list):
    print("[ASSERT] smoke_assert.yaml requires assertions[]", file=sys.stderr)
    sys.exit(2)


def fail(message: str) -> None:
    print(f"[ASSERT] {message}", file=sys.stderr)
    sys.exit(1)


def assert_http(item: dict) -> None:
    if not host_port:
        fail("http assertion requires resolved host port")
    path = str(item.get("path") or "/")
    method = str(item.get("method") or "GET").upper()
    timeout = float(item.get("timeout_seconds") or 5)
    request = urllib.request.Request(f"http://127.0.0.1:{host_port}{path}", method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = response.getcode()
            headers = "\n".join(f"{key}: {value}" for key, value in response.headers.items())
            body = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        status = exc.code
        headers = "\n".join(f"{key}: {value}" for key, value in exc.headers.items())
        body = exc.read().decode("utf-8", errors="replace")

    expected_status = item.get("expect_status")
    if expected_status is not None and status != int(expected_status):
        fail(f"http status mismatch: got {status}, want {expected_status}")
    if expected_status is None and status >= 400:
        fail(f"http status indicates failure: {status}")

    expect_text = item.get("expect_text")
    if expect_text and str(expect_text) not in body:
        fail("expected body text not found")
    forbid_text = item.get("forbid_text")
    if forbid_text and str(forbid_text) in body:
        fail("forbidden body text observed")
    expect_header = item.get("expect_header")
    if expect_header and str(expect_header).lower() not in headers.lower():
        fail("expected header text not found")
    forbid_header = item.get("forbid_header")
    if forbid_header and str(forbid_header).lower() in headers.lower():
        fail("forbidden header text observed")


def assert_tcp(item: dict) -> None:
    if not host_port:
        fail("tcp assertion requires resolved host port")
    timeout = float(item.get("timeout_seconds") or 5)
    with socket.create_connection(("127.0.0.1", int(host_port)), timeout=timeout):
        return


def assert_container_exec(item: dict) -> None:
    cmd = item.get("cmd")
    if not cmd:
        fail("container_exec assertion requires cmd")
    result = subprocess.run(
        ["docker", "exec", cid, "bash", "-lc", str(cmd)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    expected_exit = int(item.get("expect_exit", 0))
    if result.returncode != expected_exit:
        fail(f"container_exec exit mismatch: got {result.returncode}, want {expected_exit}\n{result.stdout}")
    expect_text = item.get("expect_text")
    if expect_text and str(expect_text) not in result.stdout:
        fail("container_exec expected text not found")
    forbid_text = item.get("forbid_text")
    if forbid_text and str(forbid_text) in result.stdout:
        fail("container_exec forbidden text observed")


handlers = {
    "http": assert_http,
    "tcp": assert_tcp,
    "container_exec": assert_container_exec,
}

for index, assertion in enumerate(assertions, start=1):
    if not isinstance(assertion, dict):
        fail(f"assertion {index} must be an object")
    assertion_type = str(assertion.get("type") or "").strip()
    handler = handlers.get(assertion_type)
    if handler is None:
        fail(f"unsupported assertion type: {assertion_type}")
    handler(assertion)
    print(f"[ASSERT] {assertion_type} assertion {index} passed")

print(f"[ASSERT] smoke_assert.yaml passed: {yaml_path}")
PY
}

write_solve_probe_assert_yaml() {
  local challenge_file="$1"
  local output_file="$2"
  python3 - "$challenge_file" "$output_file" <<'PY'
import sys
from pathlib import Path

import yaml

challenge_path = Path(sys.argv[1])
output_path = Path(sys.argv[2])
raw = yaml.safe_load(challenge_path.read_text(encoding="utf-8")) or {}
challenge = raw.get("challenge", {}) if isinstance(raw, dict) else {}
verification = challenge.get("verification", {}) if isinstance(challenge, dict) else {}
probe = verification.get("solve_probe", {}) if isinstance(verification, dict) else {}
if not isinstance(probe, dict) or not probe:
    raise SystemExit(3)

if isinstance(probe.get("assertions"), list):
    assertions = probe["assertions"]
else:
    assertions = [probe]

output_path.write_text(yaml.safe_dump({"assertions": assertions}, sort_keys=False, allow_unicode=True), encoding="utf-8")
print(str(output_path))
PY
}

should_run_container() {
  local example_name="$1"

  if [[ "$FULL_RUN" == "1" ]]; then
    if [[ "$example_name" == "linux-qemu-basic" && "$LINUX_QEMU_RUN_MODE" != "full" ]]; then
      return 1
    fi
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

  if [[ "$example_name" == "linux-qemu-basic" && "$LINUX_QEMU_RUN_MODE" != "full" ]]; then
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
echo "- LINUX_QEMU_RUN_MODE: ${LINUX_QEMU_RUN_MODE}"
echo "- SCENARIO_VALIDATE_RENDERED: ${SCENARIO_VALIDATE_RENDERED}"
echo "- SKIP_DOCKER: ${SKIP_DOCKER}"
echo "- SMOKE_READONLY: ${SMOKE_READONLY}"
echo "- WORK_EXAMPLES_DIR: ${WORK_EXAMPLES_DIR}"
echo "- WAIT_SECONDS: ${WAIT_SECONDS}"
if [[ ${#CASE_FILTERS[@]} -gt 0 ]]; then
  echo "- CASE_FILTERS: ${CASE_FILTERS[*]}"
fi

MATCHED_CASE_COUNT=0

while IFS= read -r dir; do
  name="$(basename "$dir")"
  challenge_yaml="${dir}/challenge.yaml"
  scenario_yaml="${dir}/scenario.yaml"
  dockerfile="${dir}/Dockerfile"
  start_sh="${dir}/start.sh"

  if ! case_selected "$name"; then
    continue
  fi
  MATCHED_CASE_COUNT=$((MATCHED_CASE_COUNT + 1))

  echo
  echo "== 测试目录: ${name} =="

  if [[ -f "$scenario_yaml" ]]; then
    scenario_out="$(mktemp -d "/tmp/ctf-scenario-${name}-XXXXXX")"
    echo "[INFO] 检测到 scenario.yaml，执行 scenario 渲染与校验"
    if ! python3 "$RENDER_SCENARIO_PY" --config "$scenario_yaml" --output "$scenario_out" --accepted --reason "trusted smoke regression"; then
      echo "[ERROR] scenario render 失败: ${name}"
      FAIL_LIST+=("${name}:scenario-render")
      rm -rf "$scenario_out"
      continue
    fi

    compose_file="${scenario_out}/docker-compose.yml"
    if [[ "$SCENARIO_VALIDATE_RENDERED" != "0" ]]; then
      if python3 "$VALIDATE_SCENARIO_PY" "$compose_file" "$scenario_out" --validate-rendered; then
        scenario_validate_rc=0
      else
        scenario_validate_rc=$?
      fi
    else
      if python3 "$VALIDATE_SCENARIO_PY" "$compose_file" "$scenario_out"; then
        scenario_validate_rc=0
      else
        scenario_validate_rc=$?
      fi
    fi
    if [[ "$scenario_validate_rc" -ne 0 ]]; then
      echo "[ERROR] scenario validate 失败: ${name}"
      FAIL_LIST+=("${name}:scenario-validate")
      rm -rf "$scenario_out"
      continue
    fi

    if [[ "$SKIP_DOCKER" == "1" ]]; then
      echo "[INFO] SKIP_DOCKER=1：scenario 仅执行 render + validate，不执行 docker compose build"
    elif command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
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

  if ! python3 "$RENDER_PY" --config "$challenge_yaml" --output "$dir" --manual --reason "trusted smoke regression"; then
    echo "[ERROR] render 失败: ${name}"
    FAIL_LIST+=("${name}:render")
    continue
  fi

  if ! bash "$VALIDATE_SH" "$dockerfile" "$start_sh" "$challenge_yaml"; then
    echo "[ERROR] validate 失败: ${name}"
    FAIL_LIST+=("${name}:validate")
    continue
  fi

  stack_id="$(get_stack_id "$challenge_yaml")"
  if [[ "$stack_id" == "linux-qemu" && "$LINUX_QEMU_RUN_MODE" == "validate-only" ]]; then
    echo "[INFO] linux-qemu 当前策略仅执行 render + validate，不执行 docker build/run"
    PASS_LIST+=("${name}:validate-only")
    continue
  fi

  if [[ "$SKIP_DOCKER" == "1" ]]; then
    echo "[INFO] SKIP_DOCKER=1：仅执行 render + validate，不执行 docker build/run"
    PASS_LIST+=("${name}:validate-only")
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

  host_port="$(resolve_host_port "$cid" "$container_port")"
  if [[ -z "${host_port}" ]]; then
    echo "[WARN] 无法解析宿主端口映射: ${name} ${container_port}/tcp"
  fi

  assert_yaml="${dir}/smoke_assert.yaml"
  if [[ ! -f "${assert_yaml}" && -f "${dir}/smoke_assert.yml" ]]; then
    assert_yaml="${dir}/smoke_assert.yml"
  fi
  if [[ -f "${assert_yaml}" ]]; then
    echo "[INFO] 执行业务断言 YAML: ${assert_yaml}"
    if ! run_smoke_assert_yaml "${assert_yaml}" "${cid}" "${host_port}" "${container_port}"; then
      echo "[ERROR] smoke_assert.yaml 失败: ${name}"
      FAIL_LIST+=("${name}:smoke-assert-yaml")
      cleanup_case "$container_name" "$image_tag"
      continue
    fi
  fi

  safe_probe_name="$(printf '%s' "$name" | tr -c 'A-Za-z0-9_.-' '-')"
  solve_probe_dir="$(mktemp -d "/tmp/ctf-solve-probe-${safe_probe_name}-XXXXXX")"
  solve_probe_yaml="${solve_probe_dir}/solve_probe.yaml"
  if write_solve_probe_assert_yaml "$challenge_yaml" "$solve_probe_yaml" >/dev/null 2>&1; then
    echo "[INFO] 执行 challenge.verification.solve_probe"
    if ! run_smoke_assert_yaml "${solve_probe_yaml}" "${cid}" "${host_port}" "${container_port}"; then
      echo "[ERROR] verification.solve_probe 失败: ${name}"
      rm -rf "${solve_probe_dir}"
      FAIL_LIST+=("${name}:solve-probe")
      cleanup_case "$container_name" "$image_tag"
      continue
    fi
  fi
  rm -rf "${solve_probe_dir}"

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
done < <(find "$WORK_EXAMPLES_DIR" -mindepth 1 -maxdepth 1 -type d | sort)

if [[ ${#CASE_FILTERS[@]} -gt 0 && "$MATCHED_CASE_COUNT" -eq 0 ]]; then
  echo "[ERROR] --case 未匹配任何 examples 子目录: ${CASE_FILTERS[*]}" >&2
  exit 2
fi

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
