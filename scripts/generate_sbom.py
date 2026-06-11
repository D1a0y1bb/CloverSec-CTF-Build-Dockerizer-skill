#!/usr/bin/env python3
"""生成 SBOM 与依赖清单（Python 主实现）。"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate SBOM assets")
    parser.add_argument("--source-dir", required=True, help="source directory")
    parser.add_argument("--output-prefix", required=True, help="dist output prefix")
    parser.add_argument("--metadata-output", help="optional SBOM metadata JSON path")
    parser.add_argument("--strict", action="store_true", help="fail when syft/docker sbom cannot generate SBOM")
    return parser.parse_args()


def iter_source_files(source_dir: Path) -> list[Path]:
    return sorted(path for path in source_dir.rglob("*") if path.is_file())


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_source_inventory_spdx(source_dir: Path, out_file: Path, reason: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    files = []
    relationships = []
    for idx, path in enumerate(iter_source_files(source_dir), start=1):
        rel = path.relative_to(source_dir).as_posix()
        spdx_id = f"SPDXRef-File-{idx}"
        files.append(
            {
                "SPDXID": spdx_id,
                "fileName": rel,
                "checksums": [{"algorithm": "SHA256", "checksumValue": sha256_file(path)}],
                "licenseConcluded": "NOASSERTION",
                "copyrightText": "NOASSERTION",
            }
        )
        relationships.append(
            {
                "spdxElementId": "SPDXRef-Package",
                "relationshipType": "CONTAINS",
                "relatedSpdxElement": spdx_id,
            }
        )

    payload = {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": source_dir.name,
        "documentNamespace": f"https://cloversec.local/sbom/{source_dir.name}/{int(datetime.now(timezone.utc).timestamp())}",
        "creationInfo": {
            "created": now,
            "creators": ["Tool: CloverSec-CTF-Build-Dockerizer source-inventory"],
            "comment": reason,
        },
        "packages": [
            {
                "name": source_dir.name,
                "SPDXID": "SPDXRef-Package",
                "downloadLocation": "NOASSERTION",
                "filesAnalyzed": True,
                "licenseConcluded": "NOASSERTION",
                "licenseDeclared": "NOASSERTION",
                "copyrightText": "NOASSERTION",
            }
        ],
        "files": files,
        "relationships": relationships,
    }
    out_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_source_inventory_cdx(source_dir: Path, out_file: Path, reason: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    components = []
    for path in iter_source_files(source_dir):
        rel = path.relative_to(source_dir).as_posix()
        components.append(
            {
                "type": "file",
                "name": rel,
                "version": "0",
                "hashes": [{"alg": "SHA-256", "content": sha256_file(path)}],
            }
        )

    payload = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "version": 1,
        "metadata": {
            "timestamp": now,
            "tools": [
                {
                    "vendor": "CloverSec",
                    "name": "CloverSec-CTF-Build-Dockerizer source-inventory",
                    "version": source_dir.name,
                }
            ],
            "component": {"type": "application", "name": source_dir.name},
            "properties": [{"name": "fallback.reason", "value": reason}],
        },
        "components": components,
    }
    out_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_source_inventory_sbom(source_dir: Path, spdx: Path, cdx: Path, reason: str) -> None:
    write_source_inventory_spdx(source_dir, spdx, reason)
    write_source_inventory_cdx(source_dir, cdx, reason)


def generate_deps_report(source_dir: Path, out_file: Path, sbom_source: str) -> None:
    lines: list[str] = []
    lines.append("# CloverSec release dependency summary")
    lines.append(f"source_dir: {source_dir.name}")
    lines.append(f"sbom_source: {sbom_source}")

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


def run_cmd(cmd: list[str], stdout_file: Path | None = None, env: dict[str, str] | None = None) -> int:
    try:
        if stdout_file is None:
            proc = subprocess.run(cmd, check=False, env=env)
        else:
            with stdout_file.open("w", encoding="utf-8") as fh:
                proc = subprocess.run(cmd, check=False, stdout=fh, stderr=subprocess.DEVNULL, env=env)
        return proc.returncode
    except FileNotFoundError:
        return 127


def syft_generate(source_dir: Path, spdx: Path, cdx: Path) -> bool:
    code_spdx = run_cmd(["syft", f"dir:{source_dir}", "-o", "spdx-json"], spdx)
    code_cdx = run_cmd(["syft", f"dir:{source_dir}", "-o", "cyclonedx-json"], cdx)
    return code_spdx == 0 and code_cdx == 0


def docker_sbom_generate(source_dir: Path, spdx: Path, cdx: Path) -> bool:
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
            return False

        try:
            code_spdx = run_cmd(["docker", "sbom", tmp_tag, "--format", "spdx-json"], spdx)
            code_cdx = run_cmd(["docker", "sbom", tmp_tag, "--format", "cyclonedx-json"], cdx)
            if code_spdx == 0 and code_cdx == 0:
                return True

            if "DOCKER_API_VERSION" not in os.environ:
                retry_env = os.environ.copy()
                retry_env["DOCKER_API_VERSION"] = "1.44"
                code_spdx = run_cmd(["docker", "sbom", tmp_tag, "--format", "spdx-json"], spdx, env=retry_env)
                code_cdx = run_cmd(["docker", "sbom", tmp_tag, "--format", "cyclonedx-json"], cdx, env=retry_env)
            return code_spdx == 0 and code_cdx == 0
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
    meta = Path(args.metadata_output).resolve() if args.metadata_output else Path(f"{out_prefix}.sbom.meta.json")
    spdx.parent.mkdir(parents=True, exist_ok=True)

    generated = False
    fallback_reason = ""
    sbom_source = "source-inventory"

    if shutil.which("syft"):
        generated = syft_generate(source_dir, spdx, cdx)
        if not generated:
            fallback_reason = "syft failed; generated source inventory SBOM"
        else:
            sbom_source = "syft"
    else:
        has_docker = shutil.which("docker") is not None
        docker_sbom_help = subprocess.run(["docker", "sbom", "--help"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0 if has_docker else False
        if docker_sbom_help:
            generated = docker_sbom_generate(source_dir, spdx, cdx)
            if not generated:
                fallback_reason = "docker sbom failed; generated source inventory SBOM"
            else:
                sbom_source = "docker-sbom"
        else:
            fallback_reason = "no syft/docker sbom available; generated source inventory SBOM"

    if not generated and args.strict:
        print(f"[ERROR] SBOM strict mode failed: {fallback_reason}", flush=True)
        meta.write_text(
            json.dumps(
                {
                    "schema_version": "1.0",
                    "source": "",
                    "strict": True,
                    "fallback_reason": fallback_reason,
                    "spdx": str(spdx),
                    "cyclonedx": str(cdx),
                    "deps": str(deps),
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return 3

    if not generated:
        write_source_inventory_sbom(source_dir, spdx, cdx, fallback_reason)

    generate_deps_report(source_dir, deps, sbom_source)
    meta.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "source": sbom_source,
                "strict": bool(args.strict),
                "fallback_reason": fallback_reason,
                "spdx": str(spdx),
                "cyclonedx": str(cdx),
                "deps": str(deps),
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    for required in (spdx, cdx, deps, meta):
        if not required.exists():
            print(f"[ERROR] missing output: {required}", flush=True)
            return 1

    print("[OK] SBOM generated:")
    print(f"  - {spdx}")
    print(f"  - {cdx}")
    print(f"  - {deps}")
    print(f"  - {meta}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
