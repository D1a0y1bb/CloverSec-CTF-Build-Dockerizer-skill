#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
EXAMPLES_DIR="${SKILL_ROOT}/examples"
VALIDATE_SH="${SCRIPT_DIR}/validate.sh"
RENDER_PY="${SCRIPT_DIR}/render.py"

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

echo "开始回归校验 examples"

for dir in "$EXAMPLES_DIR"/*; do
  [[ -d "$dir" ]] || continue

  name="$(basename "$dir")"
  dockerfile="${dir}/Dockerfile"
  start_sh="${dir}/start.sh"
  challenge_yaml="${dir}/challenge.yaml"

  echo
  echo "== 示例目录: ${name} =="

  if [[ ! -f "$dockerfile" || ! -f "$start_sh" ]]; then
    if [[ -f "$challenge_yaml" && -f "$RENDER_PY" ]]; then
      echo "[INFO] 未检测到 Dockerfile/start.sh，尝试先渲染"
      log_file="/tmp/ctf_web_render_${name}_$$_${RANDOM}.log"
      : >"$log_file"
      if python3 "$RENDER_PY" --config "$challenge_yaml" --output "$dir" >"$log_file" 2>&1; then
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
