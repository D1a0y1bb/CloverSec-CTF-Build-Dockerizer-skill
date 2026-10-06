#!/usr/bin/env python3
"""输出当前目录技术栈侦测结果与置信度。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from utils import ConfigError, detect_stack, load_stack_defs  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="检测 CTF Web 题目技术栈")
    parser.add_argument("--dir", default=".", help="扫描目录，默认当前目录")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    scan_dir = Path(args.dir).resolve()

    try:
        stacks = load_stack_defs(SKILL_ROOT / "data" / "stacks.yaml")
        best_id, confidence, details = detect_stack(scan_dir, stacks)
    except ConfigError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2

    print(f"扫描目录: {scan_dir}")
    print("候选结果:")
    for item in details:
        print(
            "- {id}: score={score}/{max_score}, confidence={conf:.1f}%, files={files}, dirs={dirs}".format(
                id=item["id"],
                score=item["score"],
                max_score=item["max_score"],
                conf=item["confidence"] * 100,
                files=item["file_hits"],
                dirs=item["dir_hits"],
            )
        )

    if best_id:
        print(f"推荐栈: {best_id}（置信度 {confidence * 100:.1f}%）")
        return 0

    print("推荐栈: 无（请显式使用 --stack）")
    return 1


if __name__ == "__main__":
    sys.exit(main())
