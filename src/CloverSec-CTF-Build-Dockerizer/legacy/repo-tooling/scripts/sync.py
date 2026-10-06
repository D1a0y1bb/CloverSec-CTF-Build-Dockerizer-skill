#!/usr/bin/env python3
"""技能目录同步（Python 主实现）。"""

from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync skill to target directory")
    parser.add_argument("--codex-dir", action="store_true", help="sync to <repo>/.codex/skills")
    parser.add_argument("--target-dir", default="", help="custom target base dir")
    return parser.parse_args()


def copy_tree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    for path in dst.rglob("*"):
        if path.is_dir() and path.name == "__pycache__":
            shutil.rmtree(path, ignore_errors=True)
        elif path.is_file() and (path.name.endswith(".pyc") or path.name == ".DS_Store"):
            path.unlink(missing_ok=True)


def main() -> int:
    args = parse_args()
    root = Path(__file__).resolve().parent.parent
    src_dir = root / "src" / "CloverSec-CTF-Build-Dockerizer"

    if args.target_dir:
        target_base = Path(args.target_dir)
        if not target_base.is_absolute():
            target_base = (root / target_base).resolve()
    elif args.codex_dir:
        target_base = root / ".codex" / "skills"
    else:
        target_base = Path(os.environ.get("CLAUDE_SKILLS_DIR", str(root / ".claude" / "skills")))

    dst_dir = target_base / "CloverSec-CTF-Build-Dockerizer"

    readme_source = src_dir / "README.md"
    if not readme_source.exists():
        readme_source = root / "README.md"

    required = [src_dir / "SKILL.md", *[src_dir / d for d in ["templates", "scripts", "data", "examples", "docs"]], readme_source]
    for path in required:
        if not path.exists():
            print(f"[ERROR] 缺少源目录必要路径: {path}")
            return 1

    try:
        dst_dir.mkdir(parents=True, exist_ok=True)
        probe = dst_dir / f".sync-write-probe.{os.getpid()}"
        probe.touch()
        probe.unlink(missing_ok=True)
    except Exception:
        print(f"[ERROR] 目标目录不可写：{dst_dir}")
        return 1

    # 先清理旧目录，再按组件复制。
    if dst_dir.exists():
        for item in dst_dir.iterdir():
            if item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
            else:
                item.unlink(missing_ok=True)

    shutil.copy2(src_dir / "SKILL.md", dst_dir / "SKILL.md")
    shutil.copy2(readme_source, dst_dir / "README.md")

    for folder in ["templates", "scripts", "data", "examples", "docs"]:
        copy_tree(src_dir / folder, dst_dir / folder)

    print(f"[OK] 已同步到 {dst_dir}")
    if readme_source != src_dir / "README.md":
        print(f"[INFO] README 来源：{readme_source}（src 缺失时自动回退）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
