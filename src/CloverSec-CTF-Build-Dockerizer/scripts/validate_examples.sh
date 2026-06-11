#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
EXAMPLES_DIR="${SKILL_ROOT}/examples"
VALIDATE_SH="${SCRIPT_DIR}/validate.sh"
RENDER_PY="${SCRIPT_DIR}/render.py"
RENDER_BUNDLE_PY="${SCRIPT_DIR}/render_bundle.py"
RENDER_SCENARIO_PY="${SCRIPT_DIR}/render_scenario.py"
VALIDATE_BUNDLE_PY="${SCRIPT_DIR}/validate_bundle.py"
VALIDATE_SCENARIO_PY="${SCRIPT_DIR}/validate_scenario.py"
IMPORT_COMPOSE_PY="${SCRIPT_DIR}/import_compose.py"

usage() {
  cat <<'USAGE'
用法：
  bash scripts/validate_examples.sh [--output-root DIR] [--in-place]

说明：
  - 默认只读校验 examples：先复制到临时目录，再在临时目录渲染或校验。
  - VALIDATE_EXAMPLES_READONLY=0 或 --in-place 可恢复旧行为，在 example 原目录写入缺失产物。
  - scenario 示例默认逐服务执行 validate.sh；SCENARIO_VALIDATE_RENDERED=0 可只校验 scenario/compose 结构。
  - KEEP_VALIDATE_EXAMPLES_ARTIFACTS=1 可保留临时输出目录。
USAGE
}

OUTPUT_ROOT="${VALIDATE_EXAMPLES_OUTPUT_ROOT:-}"
READONLY="${VALIDATE_EXAMPLES_READONLY:-1}"
KEEP_ARTIFACTS="${KEEP_VALIDATE_EXAMPLES_ARTIFACTS:-0}"
SCENARIO_VALIDATE_RENDERED="${SCENARIO_VALIDATE_RENDERED:-1}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --output-root)
      if [[ $# -lt 2 || -z "${2:-}" ]]; then
        echo "[ERROR] --output-root 需要目录参数" >&2
        exit 2
      fi
      OUTPUT_ROOT="$2"
      shift 2
      ;;
    --in-place)
      READONLY="0"
      shift
      ;;
    *)
      echo "[ERROR] 未知参数: $1" >&2
      usage
      exit 2
      ;;
  esac
done

if [[ ! -d "$EXAMPLES_DIR" ]]; then
  echo "[ERROR] examples 目录不存在: $EXAMPLES_DIR" >&2
  exit 2
fi

if [[ ! -x "$VALIDATE_SH" ]]; then
  # 允许用户直接 bash validate_examples.sh 时自动补权限
  chmod +x "$VALIDATE_SH" 2>/dev/null || true
fi

PASS_LIST=()
FAIL_LIST=()
SKIP_LIST=()
TEMP_OUTPUT_ROOT=""

if [[ "$READONLY" != "0" ]]; then
  if [[ -z "$OUTPUT_ROOT" ]]; then
    TEMP_OUTPUT_ROOT="$(mktemp -d "/tmp/ctf-validate-examples-XXXXXX")"
    OUTPUT_ROOT="$TEMP_OUTPUT_ROOT"
  else
    mkdir -p "$OUTPUT_ROOT"
  fi
fi

cleanup() {
  if [[ -n "$TEMP_OUTPUT_ROOT" && "$KEEP_ARTIFACTS" != "1" ]]; then
    rm -rf "$TEMP_OUTPUT_ROOT"
  fi
}
trap cleanup EXIT

copy_example_to_workdir() {
  local src="$1"
  local name="$2"
  local dst="${OUTPUT_ROOT}/${name}"

  rm -rf "$dst"
  mkdir -p "$dst"
  cp -a "$src/." "$dst/"
  printf '%s\n' "$dst"
}

echo "开始回归校验 examples"
echo "- READONLY: ${READONLY}"
if [[ "$READONLY" != "0" ]]; then
  echo "- OUTPUT_ROOT: ${OUTPUT_ROOT}"
fi
echo "- SCENARIO_VALIDATE_RENDERED: ${SCENARIO_VALIDATE_RENDERED}"

for dir in "$EXAMPLES_DIR"/*; do
  [[ -d "$dir" ]] || continue

  name="$(basename "$dir")"
  scenario_yaml="${dir}/scenario.yaml"
  bundle_yaml="${dir}/bundle.yaml"
  compose_yaml=""
  for candidate in "${dir}/docker-compose.yml" "${dir}/docker-compose.yaml" "${dir}/compose.yml" "${dir}/compose.yaml"; do
    if [[ -f "$candidate" ]]; then
      compose_yaml="$candidate"
      break
    fi
  done

  echo
  echo "== 示例目录: ${name} =="

  if [[ -f "$scenario_yaml" ]]; then
    echo "[INFO] 检测到 scenario.yaml，执行 scenario 渲染与校验"
    if [[ "$READONLY" != "0" && -n "$OUTPUT_ROOT" ]]; then
      scenario_out="${OUTPUT_ROOT}/${name}-scenario"
      rm -rf "$scenario_out"
      mkdir -p "$scenario_out"
    else
      scenario_out="$(mktemp -d "/tmp/ctf-validate-scenario-${name}-XXXXXX")"
    fi
    if python3 "$RENDER_SCENARIO_PY" --config "$scenario_yaml" --output "$scenario_out" --accepted --reason "trusted examples regression"; then
      if [[ "$SCENARIO_VALIDATE_RENDERED" != "0" ]]; then
        if python3 "$VALIDATE_SCENARIO_PY" "$scenario_out/docker-compose.yml" "$scenario_out" --validate-rendered; then
          validate_rc=0
        else
          validate_rc=$?
        fi
      else
        if python3 "$VALIDATE_SCENARIO_PY" "$scenario_out/docker-compose.yml" "$scenario_out"; then
          validate_rc=0
        else
          validate_rc=$?
        fi
      fi
    else
      validate_rc=$?
    fi
    if [[ "$validate_rc" -eq 0 ]]; then
      PASS_LIST+=("$name:scenario")
    else
      FAIL_LIST+=("$name:scenario")
    fi
    if [[ "$KEEP_ARTIFACTS" != "1" ]]; then
      rm -rf "$scenario_out"
    fi
    continue
  fi

  if [[ -f "$bundle_yaml" ]]; then
    echo "[INFO] 检测到 bundle.yaml，执行 bundle 渲染与校验"
    if [[ "$READONLY" != "0" && -n "$OUTPUT_ROOT" ]]; then
      bundle_out="${OUTPUT_ROOT}/${name}-bundle"
      rm -rf "$bundle_out"
      mkdir -p "$bundle_out"
    else
      bundle_out="$(mktemp -d "/tmp/ctf-validate-bundle-${name}-XXXXXX")"
    fi
    if python3 "$RENDER_BUNDLE_PY" --config "$bundle_yaml" --output "$bundle_out"; then
      if python3 "$VALIDATE_BUNDLE_PY" --bundle-dir "$bundle_out" \
        && bash "$VALIDATE_SH" "$bundle_out/Dockerfile" "$bundle_out/start.sh" "$bundle_out/challenge.yaml"; then
        validate_rc=0
      else
        validate_rc=$?
      fi
    else
      validate_rc=$?
    fi
    if [[ "$validate_rc" -eq 0 ]]; then
      PASS_LIST+=("$name:bundle")
    else
      FAIL_LIST+=("$name:bundle")
    fi
    if [[ "$KEEP_ARTIFACTS" != "1" ]]; then
      rm -rf "$bundle_out"
    fi
    continue
  fi

  if [[ -n "$compose_yaml" ]]; then
    echo "[INFO] 检测到 compose 文件，执行 scenario import draft 与可渲染子集校验"
    if [[ "$READONLY" != "0" && -n "$OUTPUT_ROOT" ]]; then
      import_out="${OUTPUT_ROOT}/${name}-compose-import"
      scenario_out="${OUTPUT_ROOT}/${name}-compose-rendered"
      rm -rf "$import_out" "$scenario_out"
      mkdir -p "$import_out" "$scenario_out"
    else
      import_out="$(mktemp -d "/tmp/ctf-validate-compose-import-${name}-XXXXXX")"
      scenario_out="$(mktemp -d "/tmp/ctf-validate-compose-rendered-${name}-XXXXXX")"
    fi
    if python3 "$IMPORT_COMPOSE_PY" --compose "$compose_yaml" --output "$import_out" --scenario-name "$name"; then
      if python3 "$RENDER_SCENARIO_PY" --config "$import_out/scenario.renderable.yaml" --output "$scenario_out" --accepted --reason "trusted examples regression" \
        && python3 "$VALIDATE_SCENARIO_PY" "$scenario_out/docker-compose.yml" "$scenario_out" --validate-rendered; then
        validate_rc=0
      else
        validate_rc=$?
      fi
    else
      validate_rc=$?
    fi
    if [[ "$validate_rc" -eq 0 ]]; then
      PASS_LIST+=("$name:compose-import")
    else
      FAIL_LIST+=("$name:compose-import")
    fi
    if [[ "$KEEP_ARTIFACTS" != "1" ]]; then
      rm -rf "$import_out" "$scenario_out"
    fi
    continue
  fi

  workdir="$dir"
  if [[ "$READONLY" != "0" ]]; then
    workdir="$(copy_example_to_workdir "$dir" "$name")"
  fi

  dockerfile="${workdir}/Dockerfile"
  start_sh="${workdir}/start.sh"
  challenge_yaml="${workdir}/challenge.yaml"

  if [[ ! -f "$dockerfile" || ! -f "$start_sh" ]]; then
    if [[ -f "$challenge_yaml" && -f "$RENDER_PY" ]]; then
      echo "[INFO] 未检测到 Dockerfile/start.sh，尝试先渲染"
      log_file="/tmp/ctf_web_render_${name}_$$_${RANDOM}.log"
      : >"$log_file"
      if python3 "$RENDER_PY" --config "$challenge_yaml" --output "$workdir" --manual --reason "trusted examples regression" >"$log_file" 2>&1; then
        echo "[INFO] 渲染成功"
        rm -f "$log_file"
      else
        echo "[ERROR] 渲染失败，输出如下："
        cat "$log_file"
        rm -f "$log_file"
        FAIL_LIST+=("$name")
        continue
      fi
    else
      echo "[WARN] 缺少 Dockerfile/start.sh 且无法渲染（无 challenge.yaml），跳过"
      SKIP_LIST+=("$name")
      continue
    fi
  fi

  if bash "$VALIDATE_SH" "$dockerfile" "$start_sh" "$challenge_yaml"; then
    PASS_LIST+=("$name")
  else
    FAIL_LIST+=("$name")
  fi
done

echo
echo "回归汇总"
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
