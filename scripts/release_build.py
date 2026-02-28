#!/usr/bin/env python3
"""发布打包构建（Python 主实现）。"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

PACKAGE_NAME = "CloverSec-CTF-Build-Dockerizer"
SKILL_SOURCE_NAME = "CloverSec-CTF-Build-Dockerizer"
VERSION_RE = re.compile(r"^v[0-9]+\.[0-9]+\.[0-9]+([a-z0-9.-]+)?$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build release artifact")
    parser.add_argument("--skip-checks", action="store_true", help="skip pre checks")
    return parser.parse_args()


def run(cmd: list[str], cwd: Path | None = None, env: dict[str, str] | None = None) -> None:
    proc = subprocess.run(cmd, cwd=str(cwd) if cwd else None, env=env, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"command failed ({proc.returncode}): {' '.join(cmd)}")


def load_version(version_file: Path) -> str:
    if not version_file.exists():
        raise RuntimeError(f"缺少 VERSION 文件: {version_file}")
    version = version_file.read_text(encoding="utf-8", errors="ignore").strip()
    if not version:
        raise RuntimeError("VERSION 文件为空")
    if not VERSION_RE.match(version):
        raise RuntimeError(f"VERSION 格式非法: {version}")
    return version


def shell_syntax_check(root: Path, skill_src: Path) -> None:
    for base in [root / "scripts", skill_src / "scripts"]:
        for script in sorted(base.rglob("*.sh")):
            run(["bash", "-n", str(script)])


def cleanup_python_cache(paths: list[Path]) -> None:
    for base in paths:
        if not base.exists():
            continue
        for file in list(base.rglob("*.pyc")) + list(base.rglob("*.pyo")) + list(base.rglob("*.pyd")):
            file.unlink(missing_ok=True)
        for folder in list(base.rglob("__pycache__")):
            shutil.rmtree(folder, ignore_errors=True)


def privacy_scan(paths: list[Path]) -> None:
    pattern = re.compile(r"/[Uu]sers/|yuque\.com/[A-Za-z0-9_-]+|By\[@")
    for path in paths:
        if path.is_file():
            text = path.read_text(encoding="utf-8", errors="ignore")
            if pattern.search(text):
                raise RuntimeError(f"公开文档存在私有信息: {path}")
        elif path.is_dir():
            for file in path.rglob("*"):
                if file.is_file():
                    text = file.read_text(encoding="utf-8", errors="ignore")
                    if pattern.search(text):
                        raise RuntimeError(f"公开目录存在私有信息: {file}")


def copy_skill_tree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    for file in list(dst.rglob(".DS_Store")):
        file.unlink(missing_ok=True)
    for file in list(dst.rglob("*.pyc")) + list(dst.rglob("*.pyo")) + list(dst.rglob("*.pyd")):
        file.unlink(missing_ok=True)
    for folder in list(dst.rglob("__pycache__")):
        shutil.rmtree(folder, ignore_errors=True)


def zip_dir(base: Path, folder_name: str, zip_path: Path) -> None:
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        target = base / folder_name
        for file in sorted(target.rglob("*")):
            if file.is_file():
                zf.write(file, arcname=str(file.relative_to(base)))


def assert_zip_layout(zip_path: Path) -> None:
    with zipfile.ZipFile(zip_path, "r") as zf:
        names = zf.namelist()
    if any("/.claude/" in name or "/.codex/" in name for name in names):
        raise RuntimeError("发布 zip 不应包含 .claude/.codex 包装层")


def main() -> int:
    args = parse_args()
    root = Path(__file__).resolve().parent.parent
    version_file = root / "VERSION"
    src_skill_dir = root / "src" / SKILL_SOURCE_NAME
    dist = root / "dist"
    sbom_script = root / "scripts" / "generate_sbom.py"

    try:
        version = load_version(version_file)
        if not src_skill_dir.exists():
            raise RuntimeError(f"技能真源目录不存在: {src_skill_dir}")
        if not sbom_script.exists():
            raise RuntimeError(f"缺少 SBOM 脚本: {sbom_script}")

        package_basename = f"{PACKAGE_NAME}-{version}"
        release_root = dist / package_basename
        zip_path = dist / f"{package_basename}.zip"

        if dist.exists():
            for stale in [release_root, zip_path, dist / "release_root", dist / "CloverSec-CTF-Build-Dockerizer-release.zip"]:
                if stale.is_dir():
                    shutil.rmtree(stale, ignore_errors=True)
                elif stale.exists():
                    stale.unlink(missing_ok=True)
        dist.mkdir(parents=True, exist_ok=True)

        if not args.skip_checks:
            print("[INFO] 执行发布前检查...")
            py_files = [str(p) for p in sorted((src_skill_dir / "scripts").glob("*.py"))]
            py_files.extend(str(p) for p in sorted((root / "scripts").glob("*.py")))
            run([sys.executable, "-m", "py_compile", *py_files])
            # py_compile 会在源码树写入 __pycache__，其中可能包含绝对路径信息，
            # 需要在私有信息扫描前清理，避免误报。
            cleanup_python_cache([root / "scripts", src_skill_dir / "scripts"])
            shell_syntax_check(root, src_skill_dir)
            env = os.environ.copy()
            env["VALIDATE_ENFORCE_DIGEST"] = "1"
            run(["bash", str(src_skill_dir / "scripts" / "validate_examples.sh")], env=env)
            privacy_scan([root / "README.md", src_skill_dir])
            run(["bash", str(root / "scripts" / "doc_guard.sh")])
        else:
            print("[WARN] 已跳过发布前检查（--skip-checks）")

        print("[INFO] 组装发布目录...")
        copy_skill_tree(src_skill_dir, release_root)

        required = ["SKILL.md", "data", "scripts", "templates", "examples", "docs"]
        for item in required:
            if not (release_root / item).exists():
                raise RuntimeError(f"发布目录缺少 {item}: {release_root}")

        if (release_root / "README.md").exists():
            raise RuntimeError(f"发布目录不应包含技能根 README.md: {release_root / 'README.md'}")
        if (release_root / "internal").exists():
            raise RuntimeError("发布目录不应包含 internal/")

        privacy_scan([release_root])

        print(f"[INFO] 生成 zip: {zip_path}")
        zip_dir(dist, package_basename, zip_path)
        assert_zip_layout(zip_path)

        print("[INFO] 生成 SBOM 与依赖清单...")
        run(
            [
                sys.executable,
                str(sbom_script),
                "--source-dir",
                str(release_root),
                "--output-prefix",
                str(dist / package_basename),
            ]
        )

        print(f"[OK] 发布目录已生成: {release_root}")
        print(f"[OK] 发布包已生成: {zip_path}")
        return 0
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
