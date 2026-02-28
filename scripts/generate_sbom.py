#!/usr/bin/env python3
"""生成 SBOM 与依赖清单（Python 主实现）。"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate SBOM assets")
    parser.add_argument("--source-dir", required=True, help="source directory")
    parser.add_argument("--output-prefix", required=True, help="dist output prefix")
    return parser.parse_args()


def write_placeholder_json(out_file: Path, fmt: str, reason: str) -> None:
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format": fmt,
        "status": "placeholder",
        "reason": reason,
    }
    out_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def generate_deps_report(source_dir: Path, out_file: Path) -> None:
    lines: list[str] = []
    lines.append("# CloverSec release dependency summary")
    lines.append(f"source_dir: {source_dir}")

    stacks_yaml = source_dir / "data" / "stacks.yaml"
    if stacks_yaml.exists():
        try:
            import yaml  # type: ignore

            raw = yaml.safe_load(stacks_yaml.read_text(encoding="utf-8")) or {}
            stacks = raw.get("stacks", []) if isinstance(raw, dict) else []
            lines.append("")
            lines.append("[base_images]")
            for item in stacks:
                if not isinstance(item, dict):
                    continue
                sid = str(item.get("id", "")).strip()
                defaults = item.get("defaults", {}) if isinstance(item.get("defaults"), dict) else {}
                base = str(defaults.get("base_image", "")).strip()
                if sid and base:
                    lines.append(f"- {sid}: {base}")
        except Exception as exc:  # pragma: no cover
            lines.append("")
            lines.append(f"[warn] failed to parse stacks.yaml: {exc}")

    patterns = [
        "**/requirements.txt",
        "**/package.json",
        "**/pyproject.toml",
        "**/pom.xml",
        "**/build.gradle",
        "**/build.gradle.kts",
    ]
    lines.append("")
    lines.append("[manifest_files]")
    count = 0
    for pat in patterns:
        for path in sorted(source_dir.glob(pat)):
            if path.is_file():
                lines.append(f"- {path.relative_to(source_dir)}")
                count += 1
    if count == 0:
        lines.append("- (none)")

    out_file.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_cmd(cmd: list[str], stdout_file: Path | None = None) -> int:
    try:
        if stdout_file is None:
            proc = subprocess.run(cmd, check=False)
        else:
            with stdout_file.open("w", encoding="utf-8") as fh:
                proc = subprocess.run(cmd, check=False, stdout=fh, stderr=subprocess.DEVNULL)
        return proc.returncode
    except FileNotFoundError:
        return 127


def syft_generate(source_dir: Path, spdx: Path, cdx: Path) -> None:
    code_spdx = run_cmd(["syft", f"dir:{source_dir}", "-o", "spdx-json"], spdx)
    if code_spdx != 0:
        write_placeholder_json(spdx, "spdx-json", "syft failed to generate SPDX")
    code_cdx = run_cmd(["syft", f"dir:{source_dir}", "-o", "cyclonedx-json"], cdx)
    if code_cdx != 0:
        write_placeholder_json(cdx, "cyclonedx-json", "syft failed to generate CycloneDX")


def docker_sbom_generate(source_dir: Path, spdx: Path, cdx: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="cloversec-sbom-") as td:
        tmp = Path(td)
        dockerfile = tmp / "Dockerfile"
        payload = tmp / "payload"
        payload.mkdir(parents=True, exist_ok=True)
        dockerfile.write_text(
            "FROM alpine:3.20\nWORKDIR /payload\nCOPY . /payload\n",
            encoding="utf-8",
        )
        for item in source_dir.iterdir():
            dst = payload / item.name
            if item.is_dir():
                shutil.copytree(item, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(item, dst)

        tmp_tag = f"cloversec-sbom-tmp:{int(datetime.now().timestamp())}"
        built = subprocess.run(["docker", "build", "-q", "-t", tmp_tag, str(tmp)], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if built.returncode != 0:
            write_placeholder_json(spdx, "spdx-json", "docker build failed for sbom fallback")
            write_placeholder_json(cdx, "cyclonedx-json", "docker build failed for sbom fallback")
            return

        try:
            code_spdx = run_cmd(["docker", "sbom", "--format", "spdx-json", tmp_tag], spdx)
            if code_spdx != 0:
                write_placeholder_json(spdx, "spdx-json", "docker sbom failed for SPDX")
            code_cdx = run_cmd(["docker", "sbom", "--format", "cyclonedx-json", tmp_tag], cdx)
            if code_cdx != 0:
                write_placeholder_json(cdx, "cyclonedx-json", "docker sbom failed for CycloneDX")
        finally:
            subprocess.run(["docker", "rmi", tmp_tag], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def main() -> int:
    args = parse_args()
    source_dir = Path(args.source_dir).resolve()
    out_prefix = Path(args.output_prefix).resolve()

    if not source_dir.is_dir():
        print(f"[ERROR] source-dir not found: {source_dir}", flush=True)
        return 2

    # Path.with_suffix() 会把版本号末尾 ".0" 当作扩展名替换，导致 v1.5.0 变成 v1.5。
    # 这里直接在前缀后拼接后缀，确保版本字符串完整保留。
    spdx = Path(f"{out_prefix}.sbom.spdx.json")
    cdx = Path(f"{out_prefix}.sbom.cdx.json")
    deps = Path(f"{out_prefix}.deps.txt")
    spdx.parent.mkdir(parents=True, exist_ok=True)

    generate_deps_report(source_dir, deps)

    if shutil.which("syft"):
        syft_generate(source_dir, spdx, cdx)
    else:
        has_docker = shutil.which("docker") is not None
        docker_sbom_help = subprocess.run(["docker", "sbom", "--help"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0 if has_docker else False
        if docker_sbom_help:
            docker_sbom_generate(source_dir, spdx, cdx)
        else:
            write_placeholder_json(spdx, "spdx-json", "no syft/docker sbom available")
            write_placeholder_json(cdx, "cyclonedx-json", "no syft/docker sbom available")

    for required in (spdx, cdx, deps):
        if not required.exists():
            print(f"[ERROR] missing output: {required}", flush=True)
            return 1

    print("[OK] SBOM generated:")
    print(f"  - {spdx}")
    print(f"  - {cdx}")
    print(f"  - {deps}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
