#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC_DIR="${ROOT_DIR}/src/CloverSec-CTF-Build-Dockerizer"
SYNC_DIRS=(templates scripts data examples docs)
SYNC_FILES=(SKILL.md)
TARGET_BASE_DIR="${CLAUDE_SKILLS_DIR:-${ROOT_DIR}/.claude/skills}"
SYNC_ERROR_LOG=""
README_SOURCE=""

usage() {
  cat <<'USAGE'
用法：
  bash scripts/sync.sh [--codex-dir] [--target-dir <dir>]

参数：
  --codex-dir         同步到 <repo>/.codex/skills/CloverSec-CTF-Build-Dockerizer
  --target-dir <dir>  指定技能根目录（目标将落在 <dir>/CloverSec-CTF-Build-Dockerizer）
  -h, --help          查看帮助

环境变量：
  CLAUDE_SKILLS_DIR   未传参数时，默认技能根目录（默认: <repo>/.claude/skills）
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --codex-dir)
      TARGET_BASE_DIR="${ROOT_DIR}/.codex/skills"
      shift
      ;;
    --target-dir)
      if [[ $# -lt 2 ]]; then
        echo "[ERROR] --target-dir 缺少参数" >&2
        exit 2
      fi
      TARGET_BASE_DIR="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[ERROR] 未知参数: $1" >&2
      usage
      exit 2
      ;;
  esac
done

if [[ "${TARGET_BASE_DIR}" != /* ]]; then
  TARGET_BASE_DIR="${ROOT_DIR}/${TARGET_BASE_DIR}"
fi

DST_DIR="${TARGET_BASE_DIR}/CloverSec-CTF-Build-Dockerizer"

if [[ -f "${SRC_DIR}/README.md" ]]; then
  README_SOURCE="${SRC_DIR}/README.md"
else
  README_SOURCE="${ROOT_DIR}/README.md"
fi

required_paths=(
)

for file_name in "${SYNC_FILES[@]}"; do
  required_paths+=("${SRC_DIR}/${file_name}")
done

for dir_name in "${SYNC_DIRS[@]}"; do
  required_paths+=("${SRC_DIR}/${dir_name}")
done

required_paths+=("${README_SOURCE}")

for path in "${required_paths[@]}"; do
  if [[ ! -e "${path}" ]]; then
    echo "[ERROR] 缺少源目录必要路径: ${path}" >&2
    exit 1
  fi
done

ensure_writable_target() {
  local base="$1"
  local dst="$2"
  local probe

  if ! mkdir -p "${dst}" 2>/dev/null; then
    echo "[ERROR] 无法创建目标目录：${dst}" >&2
    echo "        请检查目标路径是否可写，或使用 --target-dir 指定可写目录。" >&2
    exit 1
  fi

  probe="${dst}/.sync-write-probe.$$"
  if ! touch "${probe}" >/dev/null 2>&1; then
    echo "[ERROR] 目标目录不可写：${dst}" >&2
    echo "        请检查目录权限，或改用 --target-dir/CLAUDE_SKILLS_DIR 指向可写位置。" >&2
    exit 1
  fi
  rm -f "${probe}" >/dev/null 2>&1 || true

  if [[ ! -w "${base}" ]]; then
    echo "[WARN] 目标根目录可能不可写：${base}"
    echo "      若同步失败，请使用 --target-dir 指向可写目录。"
  fi
}

ensure_writable_target "${TARGET_BASE_DIR}" "${DST_DIR}"

RSYNC_EXCLUDES=(
  --exclude "__pycache__/"
  --exclude "*.pyc"
  --exclude ".DS_Store"
)
RSYNC_BASE_OPTS=(
  -r
  --links
  --perms
  --executability
  --no-times
  --no-owner
  --no-group
)

sync_with_rsync() {
  for file_name in "${SYNC_FILES[@]}"; do
    rsync "${RSYNC_BASE_OPTS[@]}" "${RSYNC_EXCLUDES[@]}" "${SRC_DIR}/${file_name}" "${DST_DIR}/${file_name}" >>"${SYNC_ERROR_LOG}" 2>&1
  done
  rsync "${RSYNC_BASE_OPTS[@]}" "${RSYNC_EXCLUDES[@]}" "${README_SOURCE}" "${DST_DIR}/README.md" >>"${SYNC_ERROR_LOG}" 2>&1
  for dir_name in "${SYNC_DIRS[@]}"; do
    mkdir -p "${DST_DIR}/${dir_name}"
    rsync "${RSYNC_BASE_OPTS[@]}" --delete --delete-excluded "${RSYNC_EXCLUDES[@]}" "${SRC_DIR}/${dir_name}/" "${DST_DIR}/${dir_name}/" >>"${SYNC_ERROR_LOG}" 2>&1
  done
}

cleanup_fallback_noise() {
  find "${DST_DIR}" -type d -name "__pycache__" -prune -exec rm -rf {} +
  find "${DST_DIR}" -type f \( -name "*.pyc" -o -name ".DS_Store" \) -delete
}

sync_with_cp() {
  for file_name in "${SYNC_FILES[@]}"; do
    cp -p "${SRC_DIR}/${file_name}" "${DST_DIR}/${file_name}"
  done
  cp -p "${README_SOURCE}" "${DST_DIR}/README.md"
  for dir_name in "${SYNC_DIRS[@]}"; do
    rm -rf "${DST_DIR:?}/${dir_name}"
    mkdir -p "${DST_DIR}/${dir_name}"
    cp -Rp "${SRC_DIR}/${dir_name}/." "${DST_DIR}/${dir_name}/"
  done
  cleanup_fallback_noise
}

SYNC_ERROR_LOG="${TMPDIR:-/tmp}/ctf-sync.$$.${RANDOM}.log"
: > "${SYNC_ERROR_LOG}"
trap 'rm -f "${SYNC_ERROR_LOG}"' EXIT

if command -v rsync >/dev/null 2>&1; then
  if ! sync_with_rsync; then
    echo "[WARN] rsync 同步失败，使用 cp 兜底同步。"
    if ! sync_with_cp 2>>"${SYNC_ERROR_LOG}"; then
      echo "[ERROR] 兜底 cp 同步也失败。详情如下：" >&2
      sed -n '1,120p' "${SYNC_ERROR_LOG}" >&2
      exit 1
    fi
  fi
else
  echo "[WARN] 未检测到 rsync，使用 cp 兜底同步。"
  if ! sync_with_cp 2>>"${SYNC_ERROR_LOG}"; then
    echo "[ERROR] cp 同步失败。详情如下：" >&2
    sed -n '1,120p' "${SYNC_ERROR_LOG}" >&2
    exit 1
  fi
fi

cleanup_fallback_noise

echo "[OK] 已同步到 ${DST_DIR}"
if [[ "${README_SOURCE}" != "${SRC_DIR}/README.md" ]]; then
  echo "[INFO] README 来源：${README_SOURCE}（src 缺失时自动回退）"
fi
