#!/usr/bin/env python3
"""文档一致性检查（Python 主实现）。"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Iterable

VERSION_RE = r"v[0-9]+\.[0-9]+\.[0-9]+(?:[a-z0-9.-]+)?"


class Counter:
    def __init__(self) -> None:
        self.error = 0
        self.warn = 0
        self.info = 0

    def log_info(self, msg: str) -> None:
        self.info += 1
        print(f"[INFO] {msg}")

    def log_warn(self, msg: str) -> None:
        self.warn += 1
        print(f"[WARN] {msg}")

    def log_error(self, msg: str) -> None:
        self.error += 1
        print(f"[ERROR] {msg}", file=sys.stderr)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="文档一致性检查")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent.parent), help="仓库根目录")
    return parser.parse_args()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def extract_readme_version(text: str) -> str:
    patterns = [
        rf"^\s*VERSION[：:]\s*({VERSION_RE})\s*$",
        rf"<strong>\s*VERSION\s*</strong>\s*[：:]\s*({VERSION_RE})",
    ]
    for pattern in patterns:
        m = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
        if m:
            return m.group(1).strip()
    return ""


def collect_doc_files(root: Path) -> list[Path]:
    skill_dir = root / "src" / "CloverSec-CTF-Build-Dockerizer"
    files: list[Path] = [root / "README.md", skill_dir / "SKILL.md"]
    docs_dir = skill_dir / "docs"
    if docs_dir.is_dir():
        files.extend(sorted(docs_dir.glob("*.md")))
    return files


def find_text_hits(files: Iterable[Path], pattern: str, flags: int = 0) -> list[str]:
    hits: list[str] = []
    regex = re.compile(pattern, flags)
    for file in files:
        text = read_text(file)
        for idx, line in enumerate(text.splitlines(), start=1):
            if regex.search(line):
                hits.append(f"{file}:{idx}:{line.strip()}")
    return hits


def normalize_candidate(raw: str) -> str:
    cand = raw.strip()
    if " " in cand:
        cand = cand.split()[0]
    cand = cand.rstrip(".,;:)]")
    return cand


def should_check_candidate(cand: str) -> bool:
    if not cand:
        return False
    if cand.startswith(("http://", "https://", "#", "/")):
        return False
    if "://" in cand:
        return False
    if "<" in cand or ">" in cand:
        return False
    if any(ch in cand for ch in ("*", "{", "}", "$", "|")):
        return False
    return cand == "README.md" or cand == "VERSION" or cand.startswith("src/") or cand.startswith("scripts/")


def check_missing_refs(root: Path, docs: Iterable[Path]) -> list[str]:
    code_re = re.compile(r"`([^`\n]+)`")
    link_re = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
    seen: set[tuple[str, str]] = set()
    missing: list[str] = []

    for doc in docs:
        text = read_text(doc)
        candidates = code_re.findall(text) + link_re.findall(text)
        for raw in candidates:
            cand = normalize_candidate(raw)
            if not should_check_candidate(cand):
                continue
            key = (str(doc), cand)
            if key in seen:
                continue
            seen.add(key)
            if not (root / cand).exists():
                missing.append(f"{doc}:{cand}")
    return missing


def check_additional_consistency(counter: Counter, docs: list[Path]) -> None:
    pwn_hits = find_text_hits(
        docs,
        r"Pwn\(xinetd\)|Pwn \(xinetd\)|xinetd 托管二进制服务",
        flags=re.IGNORECASE,
    )
    if pwn_hits:
        counter.log_warn("检测到旧 Pwn 口径（建议统一为 xinetd/tcpserver/socat）：")
        for item in pwn_hits:
            print(item, file=sys.stderr)
    else:
        counter.log_info("Pwn 口径检查通过")

    rdg_flag_hits = find_text_hits(
        docs,
        r"必须包含 /flag|固定.*flag.*必须",
        flags=re.IGNORECASE,
    )
    for item in list(rdg_flag_hits):
        if "include_flag_artifact" in item:
            rdg_flag_hits.remove(item)
    if rdg_flag_hits:
        counter.log_warn("检测到 /flag 绝对化描述（建议补充 RDG include_flag_artifact=false 例外）：")
        for item in rdg_flag_hits:
            print(item, file=sys.stderr)
    else:
        counter.log_info("/flag 契约描述检查通过")


def main() -> int:
    args = parse_args()
    root = Path(args.root).resolve()
    skill_dir = root / "src" / "CloverSec-CTF-Build-Dockerizer"
    readme = root / "README.md"
    version_file = root / "VERSION"
    skill = skill_dir / "SKILL.md"

    counter = Counter()

    if not readme.exists():
        print(f"[ERROR] 缺少 README.md: {readme}", file=sys.stderr)
        return 2
    if not skill.exists():
        print(f"[ERROR] 缺少 SKILL.md: {skill}", file=sys.stderr)
        return 2
    if not version_file.exists():
        print(f"[ERROR] 缺少 VERSION 文件: {version_file}", file=sys.stderr)
        return 2

    docs = collect_doc_files(root)
    counter.log_info("开始文档治理检查（README + SKILL + docs）")

    banned_hits = find_text_hits(docs, r"wechat_hub_campaign_article\.md")
    if banned_hits:
        counter.log_error("检测到被禁用文档引用 wechat_hub_campaign_article.md：")
        for item in banned_hits:
            print(item, file=sys.stderr)
    else:
        counter.log_info("未检测到被禁用文档引用 wechat_hub_campaign_article.md")

    missing_src_readme = find_text_hits(docs, r"src/CloverSec-CTF-Build-Dockerizer/README\.md")
    if missing_src_readme:
        counter.log_error("检测到不存在路径引用 src/CloverSec-CTF-Build-Dockerizer/README.md：")
        for item in missing_src_readme:
            print(item, file=sys.stderr)
    else:
        counter.log_info("未检测到不存在路径引用 src/CloverSec-CTF-Build-Dockerizer/README.md")

    legacy_hits = find_text_hits(docs, r"ctf-web-dockerizer", flags=re.IGNORECASE)
    if legacy_hits:
        counter.log_error("检测到旧名 ctf-web-dockerizer 残留：")
        for item in legacy_hits:
            print(item, file=sys.stderr)
    else:
        counter.log_info("公开文档未检测到旧名 ctf-web-dockerizer 残留")

    missing_refs = check_missing_refs(root, docs)
    if missing_refs:
        counter.log_error("检测到文档失效路径引用：")
        for item in missing_refs:
            print(item, file=sys.stderr)
    else:
        counter.log_info("文档路径引用检查通过（引用目标均存在）")

    repo_version = version_file.read_text(encoding="utf-8", errors="ignore").strip()
    readme_version = extract_readme_version(read_text(readme))
    if not readme_version:
        counter.log_warn("README 缺少可解析的 VERSION 元信息")
    elif readme_version != repo_version:
        counter.log_warn(f"README 顶部 VERSION({readme_version}) 与 VERSION 文件({repo_version}) 不一致")
    else:
        counter.log_info("README 顶部 VERSION 与 VERSION 文件一致")

    text = read_text(readme)
    phase_template_enabled = bool(
        re.search(r"^\| Phase \| ", text, flags=re.MULTILINE)
        or re.search(r"^\| Phase [0-9]+(\b| /)", text, flags=re.MULTILINE)
    )
    if phase_template_enabled:
        if re.search(r"^\| Phase \| 日期 \| 目标 \| 关键产出 \| 验收结果 \|$", text, flags=re.MULTILINE):
            counter.log_info("Phase 回填表头字段完整")
        else:
            counter.log_warn("README 缺少标准 Phase 回填表头")

        for idx in range(1, 11):
            if not re.search(rf"\| Phase {idx}(\b| /)", text):
                counter.log_warn(f"README 未检测到 Phase {idx} 行")
    else:
        counter.log_info("README 未启用 Phase 回填模板，跳过 Phase 行检查")

    check_additional_consistency(counter, docs)

    print("\n文档检查汇总")
    print(f"- ERROR: {counter.error}")
    print(f"- WARN:  {counter.warn}")
    print(f"- INFO:  {counter.info}")

    if counter.error > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
