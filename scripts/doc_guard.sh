#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILL_DIR="${ROOT_DIR}/src/CloverSec-CTF-Build-Dockerizer"
README_FILE="${ROOT_DIR}/README.md"
VERSION_FILE="${ROOT_DIR}/VERSION"

ERROR_COUNT=0
WARN_COUNT=0
INFO_COUNT=0

info() {
  INFO_COUNT=$((INFO_COUNT + 1))
  echo "[INFO] $*"
}

warn() {
  WARN_COUNT=$((WARN_COUNT + 1))
  echo "[WARN] $*"
}

error() {
  ERROR_COUNT=$((ERROR_COUNT + 1))
  echo "[ERROR] $*" >&2
}

if [[ ! -f "${README_FILE}" ]]; then
  echo "[ERROR] 缺少 README.md: ${README_FILE}" >&2
  exit 2
fi

if [[ ! -f "${SKILL_DIR}/SKILL.md" ]]; then
  echo "[ERROR] 缺少 SKILL.md: ${SKILL_DIR}/SKILL.md" >&2
  exit 2
fi

if [[ ! -f "${VERSION_FILE}" ]]; then
  echo "[ERROR] 缺少 VERSION 文件: ${VERSION_FILE}" >&2
  exit 2
fi

DOC_FILES=(
  "${README_FILE}"
  "${SKILL_DIR}/SKILL.md"
)

while IFS= read -r doc; do
  DOC_FILES+=("${doc}")
done < <(find "${SKILL_DIR}/docs" -maxdepth 1 -type f -name '*.md' | sort)

info "开始文档治理检查（README + SKILL + docs）"

if rg -n "wechat_hub_campaign_article\.md" "${DOC_FILES[@]}" >/tmp/doc_guard_wechat.$$ 2>&1; then
  error "检测到被禁用文档引用 wechat_hub_campaign_article.md："
  cat /tmp/doc_guard_wechat.$$ >&2
else
  info "未检测到被禁用文档引用 wechat_hub_campaign_article.md"
fi
rm -f /tmp/doc_guard_wechat.$$ >/dev/null 2>&1 || true

if rg -n "src/CloverSec-CTF-Build-Dockerizer/README\.md" "${DOC_FILES[@]}" >/tmp/doc_guard_missing_readme.$$ 2>&1; then
  error "检测到不存在路径引用 src/CloverSec-CTF-Build-Dockerizer/README.md："
  cat /tmp/doc_guard_missing_readme.$$ >&2
else
  info "未检测到不存在路径引用 src/CloverSec-CTF-Build-Dockerizer/README.md"
fi
rm -f /tmp/doc_guard_missing_readme.$$ >/dev/null 2>&1 || true

if rg -n -i "ctf-web-dockerizer" "${DOC_FILES[@]}" >/tmp/doc_guard_legacy.$$ 2>&1; then
  error "检测到旧名 ctf-web-dockerizer 残留（公开文档要求只使用新名）："
  cat /tmp/doc_guard_legacy.$$ >&2
else
  info "公开文档未检测到旧名 ctf-web-dockerizer 残留"
fi
rm -f /tmp/doc_guard_legacy.$$ >/dev/null 2>&1 || true

TMP_MISSING_REFS="$(mktemp -t doc-guard-missing-refs.XXXXXX)"
trap 'rm -f "${TMP_MISSING_REFS}"' EXIT

python3 - "${ROOT_DIR}" "${DOC_FILES[@]}" >"${TMP_MISSING_REFS}" <<'PY'
import re
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
docs = [Path(p) for p in sys.argv[2:]]

code_re = re.compile(r"`([^`\n]+)`")
link_re = re.compile(r"\[[^\]]+\]\(([^)]+)\)")

def normalize_candidate(raw: str) -> str:
    cand = raw.strip()
    if " " in cand:
        cand = cand.split()[0]
    cand = cand.rstrip(".,;:)]")
    return cand

def should_check(cand: str) -> bool:
    if not cand:
        return False
    if cand.startswith(("http://", "https://", "#", "/")):
        return False
    if "://" in cand:
        return False
    if cand.startswith("<") and cand.endswith(">"):
        return False
    if "<" in cand or ">" in cand:
        return False
    if any(ch in cand for ch in ("*", "{", "}", "$", "|")):
        return False
    return (
        cand == "README.md"
        or cand == "VERSION"
        or cand.startswith("src/")
        or cand.startswith("scripts/")
    )

seen = set()
missing = []

for doc in docs:
    text = doc.read_text(encoding="utf-8", errors="ignore")
    candidates = []
    candidates.extend(code_re.findall(text))
    candidates.extend(link_re.findall(text))

    for raw in candidates:
        cand = normalize_candidate(raw)
        if not should_check(cand):
            continue
        key = (str(doc), cand)
        if key in seen:
            continue
        seen.add(key)

        path = (root / cand).resolve()
        if not path.exists():
            missing.append(f"{doc}:{cand}")

for item in missing:
    print(item)
PY

missing_refs="$(cat "${TMP_MISSING_REFS}")"

if [[ -n "${missing_refs}" ]]; then
  error "检测到文档失效路径引用："
  printf '%s\n' "${missing_refs}" >&2
else
  info "文档路径引用检查通过（引用目标均存在）"
fi

repo_version="$(tr -d '[:space:]' < "${VERSION_FILE}")"
readme_version="$(rg -n '^VERSION：' "${README_FILE}" | head -n1 | sed 's/^[0-9]*:VERSION：//' | tr -d '[:space:]' || true)"

if [[ -z "${readme_version}" ]]; then
  warn "README 顶部缺少 VERSION：<版本号> 元信息"
elif [[ "${readme_version}" != "${repo_version}" ]]; then
  warn "README 顶部 VERSION(${readme_version}) 与 VERSION 文件(${repo_version}) 不一致"
else
  info "README 顶部 VERSION 与 VERSION 文件一致"
fi

if rg -q '^\| Phase \| 日期 \| 目标 \| 关键产出 \| 验收结果 \|$' "${README_FILE}"; then
  info "Phase 回填表头字段完整"
else
  warn "README 缺少标准 Phase 回填表头：| Phase | 日期 | 目标 | 关键产出 | 验收结果 |"
fi

for i in $(seq 1 10); do
  if rg -q "\\| Phase ${i}(\\b| /)" "${README_FILE}"; then
    :
  else
    warn "README 未检测到 Phase ${i} 行"
  fi
done

echo
echo "文档检查汇总"
echo "- ERROR: ${ERROR_COUNT}"
echo "- WARN:  ${WARN_COUNT}"
echo "- INFO:  ${INFO_COUNT}"

if [[ ${ERROR_COUNT} -gt 0 ]]; then
  exit 1
fi

exit 0
