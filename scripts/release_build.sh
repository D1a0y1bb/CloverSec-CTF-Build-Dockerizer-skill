#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILL_SOURCE_NAME="CloverSec-CTF-Build-Dockerizer"
PACKAGE_NAME="CloverSec-CTF-Build-Dockerizer"
VERSION_FILE="${ROOT_DIR}/VERSION"
SRC_SKILL_DIR="${ROOT_DIR}/src/${SKILL_SOURCE_NAME}"
DIST_DIR="${ROOT_DIR}/dist"
GENERATE_SBOM_SCRIPT="${ROOT_DIR}/scripts/generate_sbom.sh"
SKIP_CHECKS="false"
RELEASE_VERSION=""
PACKAGE_BASENAME=""
RELEASE_ROOT=""
ZIP_PATH=""

usage() {
  cat <<'USAGE'
用法：
  bash scripts/release_build.sh [--skip-checks]

说明：
  - 版本号读取自根目录 VERSION（例如 v1.2.0）
  - 生成带版本号的产物：
      dist/CloverSec-CTF-Build-Dockerizer-<VERSION>/
      dist/CloverSec-CTF-Build-Dockerizer-<VERSION>.zip
      dist/CloverSec-CTF-Build-Dockerizer-<VERSION>.sbom.spdx.json
      dist/CloverSec-CTF-Build-Dockerizer-<VERSION>.sbom.cdx.json
      dist/CloverSec-CTF-Build-Dockerizer-<VERSION>.deps.txt
  - zip 为单目录分发，不包含 .claude/.codex 双树
  - 技能根目录不包含 README.md（避免部分 Agent 误识别）
  - 包内排除 internal、.DS_Store、__pycache__、*.pyc
USAGE
}

load_release_version() {
  if [[ ! -f "${VERSION_FILE}" ]]; then
    echo "[ERROR] 缺少 VERSION 文件: ${VERSION_FILE}" >&2
    echo "[ERROR] 请在仓库根目录创建 VERSION，例如: v1.2.0" >&2
    exit 1
  fi

  RELEASE_VERSION="$(tr -d '[:space:]' < "${VERSION_FILE}")"
  if [[ -z "${RELEASE_VERSION}" ]]; then
    echo "[ERROR] VERSION 文件为空，请填写版本号，例如: v1.2.0" >&2
    exit 1
  fi

  if [[ ! "${RELEASE_VERSION}" =~ ^v[0-9]+\.[0-9]+\.[0-9]+([a-z0-9.-]+)?$ ]]; then
    echo "[ERROR] VERSION 格式非法: ${RELEASE_VERSION}" >&2
    echo "[ERROR] 允许格式示例: v1.2.0 或 v1.2.0-rc.1" >&2
    exit 1
  fi

  PACKAGE_BASENAME="${PACKAGE_NAME}-${RELEASE_VERSION}"
  RELEASE_ROOT="${DIST_DIR}/${PACKAGE_BASENAME}"
  ZIP_PATH="${DIST_DIR}/${PACKAGE_BASENAME}.zip"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-checks)
      SKIP_CHECKS="true"
      shift
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

load_release_version

if [[ ! -d "${SRC_SKILL_DIR}" ]]; then
  echo "[ERROR] 技能真源目录不存在: ${SRC_SKILL_DIR}" >&2
  exit 1
fi

if ! command -v zip >/dev/null 2>&1; then
  echo "[ERROR] 系统缺少 zip 命令，请先安装 zip。" >&2
  exit 1
fi

if [[ ! -x "${GENERATE_SBOM_SCRIPT}" ]]; then
  echo "[ERROR] 缺少 SBOM 生成脚本: ${GENERATE_SBOM_SCRIPT}" >&2
  exit 1
fi

run_checks() {
  echo "[INFO] 执行发布前检查..."

  echo "[INFO] Python 语法检查"
  python3 -m py_compile "${SRC_SKILL_DIR}"/scripts/*.py

  echo "[INFO] Shell 语法检查"
  find "${ROOT_DIR}/scripts" "${SRC_SKILL_DIR}/scripts" -name '*.sh' -print0 | xargs -0 -n1 bash -n

  echo "[INFO] 示例静态回归（启用发布级 digest 门禁）"
  VALIDATE_ENFORCE_DIGEST=1 bash "${SRC_SKILL_DIR}/scripts/validate_examples.sh"

  echo "[INFO] 公开文档隐私扫描"
  if rg -n --hidden --glob '!.git' --glob '!internal/**' '/[Uu]sers/|yuque\\.com/[A-Za-z0-9_-]+|By\[@' \
    "${ROOT_DIR}/README.md" "${SRC_SKILL_DIR}"; then
    echo "[ERROR] 公开文档存在私有信息，请修复后重试。" >&2
    exit 1
  fi

  echo "[INFO] 文档一致性检查"
  bash "${ROOT_DIR}/scripts/doc_guard.sh"
}

copy_skill_tree() {
  local dst="$1"
  mkdir -p "${dst}"

  if command -v rsync >/dev/null 2>&1; then
    rsync -a --delete \
      --exclude '.DS_Store' \
      --exclude '__pycache__/' \
      --exclude '*.pyc' \
      --exclude '*.pyo' \
      --exclude '*.pyd' \
      "${SRC_SKILL_DIR}/" "${dst}/"
  else
    rm -rf "${dst:?}"/*
    cp -R "${SRC_SKILL_DIR}/." "${dst}/"
    find "${dst}" -name '.DS_Store' -o -name '__pycache__' -o -name '*.pyc' | while IFS= read -r f; do
      rm -rf "$f"
    done
  fi

}

verify_skill_dir() {
  local base="$1"
  local required=(SKILL.md data scripts templates examples docs)

  for item in "${required[@]}"; do
    if [[ ! -e "${base}/${item}" ]]; then
      echo "[ERROR] 发布目录缺少 ${item}: ${base}" >&2
      exit 1
    fi
  done
}

assert_no_root_readme() {
  local base="$1"
  if [[ -f "${base}/README.md" ]]; then
    echo "[ERROR] 发布目录不应包含技能根 README.md: ${base}/README.md" >&2
    exit 1
  fi
}

assert_zip_layout() {
  local zip_file="$1"
  if [[ ! -f "$zip_file" ]]; then
    echo "[ERROR] 发布 zip 不存在: ${zip_file}" >&2
    exit 1
  fi

  if unzip -l "$zip_file" | rg -q '/\.claude/|/\.codex/'; then
    echo "[ERROR] 发布 zip 不应包含 .claude/.codex 包装层。" >&2
    exit 1
  fi
}

mkdir -p "${DIST_DIR}"
rm -rf \
  "${RELEASE_ROOT}" \
  "${ZIP_PATH}" \
  "${DIST_DIR}/release_root" \
  "${DIST_DIR}/CloverSec-CTF-Build-Dockerizer-release.zip"

if [[ "${SKIP_CHECKS}" != "true" ]]; then
  run_checks
else
  echo "[WARN] 已跳过发布前检查（--skip-checks）"
fi

echo "[INFO] 组装发布目录..."
copy_skill_tree "${RELEASE_ROOT}"
verify_skill_dir "${RELEASE_ROOT}"
assert_no_root_readme "${RELEASE_ROOT}"

if [[ -d "${RELEASE_ROOT}/internal" ]]; then
  echo "[ERROR] 发布目录不应包含 internal/" >&2
  exit 1
fi

if rg -n '/[Uu]sers/|yuque\\.com/[A-Za-z0-9_-]+|By\[@' "${RELEASE_ROOT}"; then
  echo "[ERROR] 发布目录仍含私有信息。" >&2
  exit 1
fi

echo "[INFO] 生成 zip: ${ZIP_PATH}"
(
  cd "${DIST_DIR}"
  zip -rq "${ZIP_PATH}" "${PACKAGE_BASENAME}"
)

if [[ ! -d "${RELEASE_ROOT}" ]]; then
  echo "[ERROR] 发布目录不存在: ${RELEASE_ROOT}" >&2
  exit 1
fi

assert_zip_layout "${ZIP_PATH}"

echo "[INFO] 生成 SBOM 与依赖清单..."
bash "${GENERATE_SBOM_SCRIPT}" \
  --source-dir "${RELEASE_ROOT}" \
  --output-prefix "${DIST_DIR}/${PACKAGE_BASENAME}"

echo "[OK] 发布目录已生成: ${RELEASE_ROOT}"
echo "[OK] 发布包已生成: ${ZIP_PATH}"
echo "[INFO] 包内顶层结构："
unzip -l "${ZIP_PATH}" | awk 'NR<=40 {print}'
