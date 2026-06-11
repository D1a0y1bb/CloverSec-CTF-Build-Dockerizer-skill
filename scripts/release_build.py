#!/usr/bin/env python3
"""发布打包构建（Python 主实现）。"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

PACKAGE_NAME = "CloverSec-CTF-Build-Dockerizer"
SKILL_SOURCE_NAME = "CloverSec-CTF-Build-Dockerizer"
SKILL_SLUG = "cloversec-ctf-build-dockerizer"
VERSION_RE = re.compile(r"^v[0-9]+\.[0-9]+\.[0-9]+([a-z0-9.-]+)?$")
SKILL_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build release artifact")
    parser.add_argument("--skip-checks", action="store_true", help="skip pre checks")
    parser.add_argument("--with-smoke", action="store_true", help="run Docker smoke test during release build")
    parser.add_argument("--skip-smoke-with-reason", default="", help="skip smoke test with an explicit reason")
    parser.add_argument("--sbom-strict", action="store_true", help="require syft/docker sbom instead of source-inventory fallback")
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


def load_skill_name(skill_file: Path) -> str:
    text = skill_file.read_text(encoding="utf-8", errors="ignore")
    if not text.startswith("---"):
        raise RuntimeError(f"SKILL.md 缺少 frontmatter: {skill_file}")
    end = text.find("\n---", 3)
    if end == -1:
        raise RuntimeError(f"SKILL.md frontmatter 未结束: {skill_file}")
    frontmatter = text[3:end]
    for line in frontmatter.splitlines():
        if line.startswith("name:"):
            return line.split(":", 1)[1].strip().strip("\"'")
    raise RuntimeError(f"SKILL.md frontmatter 缺少 name: {skill_file}")


def assert_skillhub_slug(skill_file: Path) -> None:
    name = load_skill_name(skill_file)
    if not SKILL_SLUG_RE.fullmatch(name):
        raise RuntimeError(f"SKILL.md frontmatter name 不符合 SkillHub slug 规则: {name}")
    if name != SKILL_SLUG:
        raise RuntimeError(f"SKILL.md frontmatter name 应为 {SKILL_SLUG}: {name}")


def assert_skill_metadata(skill_dir: Path) -> None:
    meta = skill_dir / "agents" / "openai.yaml"
    if not meta.is_file():
        raise RuntimeError(f"缺少 SkillHub metadata: {meta}")
    try:
        import yaml  # type: ignore
    except ModuleNotFoundError as exc:
        raise RuntimeError("检查 agents/openai.yaml 需要 PyYAML") from exc
    raw = yaml.safe_load(meta.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise RuntimeError(f"agents/openai.yaml 顶层必须是对象: {meta}")
    interface = raw.get("interface") if isinstance(raw.get("interface"), dict) else {}
    policy = raw.get("policy") if isinstance(raw.get("policy"), dict) else {}
    required = {
        "interface.display_name": interface.get("display_name"),
        "interface.short_description": interface.get("short_description"),
        "interface.brand_color": interface.get("brand_color"),
        "interface.default_prompt": interface.get("default_prompt"),
        "policy.allow_implicit_invocation": policy.get("allow_implicit_invocation"),
    }
    missing = [key for key, value in required.items() if value in (None, "")]
    if missing:
        raise RuntimeError(f"agents/openai.yaml 缺少字段: {', '.join(missing)}")


def assert_changelog_has_version(root: Path, version: str) -> None:
    path = root / "CHANGELOG.md"
    if not path.is_file():
        raise RuntimeError(f"缺少 CHANGELOG.md: {path}")
    text = path.read_text(encoding="utf-8", errors="ignore")
    pattern = re.compile(rf"^##\s+{re.escape(version)}(?:\s|$)", re.MULTILINE)
    if not pattern.search(text):
        raise RuntimeError(f"CHANGELOG.md 缺少当前版本标题: {version}")


def new_status(version: str, package_basename: str) -> dict:
    return {
        "schema_version": "1.0",
        "version": version,
        "package": package_basename,
        "checks": [],
        "smoke": {"executed": False, "skipped": False, "reason": ""},
        "skillhub_metadata": {"ok": False, "file": "agents/openai.yaml"},
        "sbom": {"source": "", "metadata_file": "", "strict": False},
        "release_ready": False,
    }


def record_check(status: dict, name: str, ok: bool, *, skipped: bool = False, reason: str = "") -> None:
    status["checks"].append({"name": name, "ok": bool(ok), "skipped": bool(skipped), "reason": reason})


def write_release_status(path: Path, status: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_check(status: dict, name: str, cmd: list[str], cwd: Path | None = None, env: dict[str, str] | None = None) -> None:
    run(cmd, cwd=cwd, env=env)
    record_check(status, name, True)


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


def git_status_snapshot(root: Path) -> bytes:
    proc = subprocess.run(
        ["git", "-C", str(root), "status", "--porcelain", "-z"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.decode("utf-8", errors="ignore").strip())
    return proc.stdout


def assert_checks_did_not_modify_source(root: Path, before: bytes) -> None:
    after = git_status_snapshot(root)
    if after == before:
        return
    proc = subprocess.run(
        ["git", "-C", str(root), "status", "--short"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    detail = proc.stdout.strip() or proc.stderr.strip() or "unknown git status change"
    raise RuntimeError(f"发布前检查修改了源码树，请先手动审查这些变更：\n{detail}")


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


def iter_files(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            files.extend(file for file in sorted(path.rglob("*")) if file.is_file())
    return files


def assert_no_trailing_whitespace(paths: list[Path]) -> None:
    hits: list[str] = []
    for file in iter_files(paths):
        data = file.read_bytes()
        if b"\0" in data:
            continue
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            continue
        for line_no, line in enumerate(text.splitlines(keepends=True), start=1):
            content = line.rstrip("\r\n")
            if content.endswith((" ", "\t")):
                hits.append(f"{file}:{line_no}: trailing whitespace")
    if hits:
        preview = "\n".join(hits[:50])
        more = "" if len(hits) <= 50 else f"\n... and {len(hits) - 50} more"
        raise RuntimeError(f"公开发布文件存在行尾空格:\n{preview}{more}")


def is_git_ignored(repo_root: Path, path: Path) -> bool:
    try:
        rel = path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return False
    proc = subprocess.run(
        ["git", "-C", str(repo_root), "check-ignore", "-q", "--", rel],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return proc.returncode == 0


def copy_skill_tree(src: Path, dst: Path, repo_root: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True, exist_ok=True)
    for item in sorted(src.rglob("*")):
        if is_git_ignored(repo_root, item):
            continue
        rel = item.relative_to(src)
        target = dst / rel
        if item.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        elif item.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)
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
    status: dict | None = None
    status_path: Path | None = None

    try:
        version = load_version(version_file)
        package_basename = f"{PACKAGE_NAME}-{version}"
        status_path = dist / f"{package_basename}.release-status.json"
        status = new_status(version, package_basename)
        status["sbom"]["strict"] = bool(args.sbom_strict)
        if args.with_smoke and args.skip_smoke_with_reason:
            raise RuntimeError("--with-smoke 与 --skip-smoke-with-reason 不能同时使用")
        if not src_skill_dir.exists():
            raise RuntimeError(f"技能真源目录不存在: {src_skill_dir}")
        if not sbom_script.exists():
            raise RuntimeError(f"缺少 SBOM 脚本: {sbom_script}")
        assert_skillhub_slug(src_skill_dir / "SKILL.md")
        record_check(status, "skillhub_slug", True)
        assert_skill_metadata(src_skill_dir)
        status["skillhub_metadata"]["ok"] = True
        record_check(status, "skillhub_metadata", True)
        assert_changelog_has_version(root, version)
        record_check(status, "changelog_current_version", True)
        assert_no_trailing_whitespace([src_skill_dir])
        record_check(status, "trailing_whitespace", True)

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
            status_before_checks = git_status_snapshot(root)
            py_files = [str(p) for p in sorted((src_skill_dir / "scripts").glob("*.py"))]
            py_files.extend(str(p) for p in sorted((root / "scripts").glob("*.py")))
            run_check(status, "py_compile", [sys.executable, "-m", "py_compile", *py_files])
            # py_compile 会在源码树写入 __pycache__，其中可能包含绝对路径信息，
            # 需要在私有信息扫描前清理，避免误报。
            cleanup_python_cache([root / "scripts", src_skill_dir / "scripts"])
            shell_syntax_check(root, src_skill_dir)
            record_check(status, "shell_syntax", True)
            env = os.environ.copy()
            env["VALIDATE_ENFORCE_DIGEST"] = "1"
            run_check(status, "validate_examples", ["bash", str(src_skill_dir / "scripts" / "validate_examples.sh")], env=env)
            # validate_examples 会触发 Python 脚本执行并再次生成 __pycache__，
            # 需要在隐私扫描前做二次清理，避免绝对路径残留导致误报。
            cleanup_python_cache([root / "scripts", src_skill_dir / "scripts"])
            privacy_scan([root / "README.md", src_skill_dir])
            record_check(status, "privacy_scan", True)
            run_check(status, "doc_guard", ["bash", str(root / "scripts" / "doc_guard.sh")])
            if args.with_smoke:
                run_check(status, "smoke_test", ["bash", str(src_skill_dir / "scripts" / "smoke_test.sh")])
                status["smoke"] = {"executed": True, "skipped": False, "reason": ""}
            elif args.skip_smoke_with_reason:
                status["smoke"] = {"executed": False, "skipped": True, "reason": args.skip_smoke_with_reason}
                record_check(status, "smoke_test", True, skipped=True, reason=args.skip_smoke_with_reason)
            else:
                status["smoke"] = {"executed": False, "skipped": True, "reason": "not requested"}
                record_check(status, "smoke_test", False, skipped=True, reason="not requested")
            cleanup_python_cache([root / "scripts", src_skill_dir / "scripts"])
            assert_checks_did_not_modify_source(root, status_before_checks)
            record_check(status, "source_tree_unchanged", True)
        else:
            print("[WARN] 已跳过发布前检查（--skip-checks）")
            record_check(status, "pre_checks", True, skipped=True, reason="--skip-checks")
            status["smoke"] = {"executed": False, "skipped": True, "reason": "--skip-checks"}

        print("[INFO] 组装发布目录...")
        copy_skill_tree(src_skill_dir, release_root, root)

        required = ["SKILL.md", "agents", "data", "scripts", "templates", "examples", "docs"]
        for item in required:
            if not (release_root / item).exists():
                raise RuntimeError(f"发布目录缺少 {item}: {release_root}")
        record_check(status, "release_required_paths", True)

        if (release_root / "README.md").exists():
            raise RuntimeError(f"发布目录不应包含技能根 README.md: {release_root / 'README.md'}")
        if (release_root / "internal").exists():
            raise RuntimeError("发布目录不应包含 internal/")

        privacy_scan([release_root])
        assert_skillhub_slug(release_root / "SKILL.md")
        assert_no_trailing_whitespace([release_root])
        record_check(status, "release_tree_validation", True)

        print(f"[INFO] 生成 zip: {zip_path}")
        zip_dir(dist, package_basename, zip_path)
        assert_zip_layout(zip_path)
        record_check(status, "zip_layout", True)

        print("[INFO] 生成 SBOM 与依赖清单...")
        sbom_meta = Path(f"{dist / package_basename}.sbom.meta.json")
        sbom_cmd = [
            sys.executable,
            str(sbom_script),
            "--source-dir",
            str(release_root),
            "--output-prefix",
            str(dist / package_basename),
            "--metadata-output",
            str(sbom_meta),
        ]
        if args.sbom_strict:
            sbom_cmd.append("--strict")
        run(sbom_cmd)
        if sbom_meta.exists():
            meta = json.loads(sbom_meta.read_text(encoding="utf-8"))
            status["sbom"]["source"] = str(meta.get("source") or "")
            status["sbom"]["metadata_file"] = str(sbom_meta)
            status["sbom"]["strict"] = bool(meta.get("strict"))
        record_check(status, "sbom", True)

        status["release_ready"] = (
            not args.skip_checks
            and (status["smoke"].get("executed") or bool(status["smoke"].get("reason") and status["smoke"].get("reason") != "not requested"))
        )
        write_release_status(status_path, status)

        print(f"[OK] 发布目录已生成: {release_root}")
        print(f"[OK] 发布包已生成: {zip_path}")
        print(f"[OK] 发布状态已生成: {status_path}")
        return 0
    except Exception as exc:
        if status is not None and status_path is not None:
            status["release_ready"] = False
            status["error"] = str(exc)
            try:
                write_release_status(status_path, status)
            except Exception:
                pass
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
