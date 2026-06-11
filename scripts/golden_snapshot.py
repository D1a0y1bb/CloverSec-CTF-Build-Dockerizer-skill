#!/usr/bin/env python3
"""Render deterministic sample outputs and compare them with a hash manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "src" / "CloverSec-CTF-Build-Dockerizer"
MANIFEST = ROOT / "tests" / "golden" / "snapshots.json"


CASES: dict[str, dict[str, Any]] = {
    "node-basic": {
        "description": "Low-risk single challenge render",
        "cwd": SKILL / "examples" / "node-basic",
        "command": [
            sys.executable,
            str(SKILL / "scripts" / "render.py"),
            "--config",
            "challenge.yaml",
            "--output",
            "{out}",
        ],
        "files": ["Dockerfile", "start.sh", "changeflag.sh"],
    },
    "bundle-legacy-centos7-webstack": {
        "description": "Fixed Bundle/Recipe render",
        "cwd": SKILL / "examples" / "bundle-legacy-centos7-webstack",
        "command": [
            sys.executable,
            str(SKILL / "scripts" / "render_bundle.py"),
            "--config",
            "bundle.yaml",
            "--output",
            "{out}",
        ],
        "files": ["Dockerfile", "start.sh", "changeflag.sh", "challenge.yaml"],
    },
    "scenario-vulhub-like-basic": {
        "description": "Scenario render with challenge and component services",
        "cwd": SKILL / "examples" / "scenario-vulhub-like-basic",
        "command": [
            sys.executable,
            str(SKILL / "scripts" / "render_scenario.py"),
            "--config",
            "scenario.yaml",
            "--output",
            "{out}",
            "--accepted",
            "--reason",
            "golden snapshot trusted regression",
        ],
        "files": [
            "docker-compose.yml",
            "services/web1/Dockerfile",
            "services/web1/start.sh",
            "services/web1/changeflag.sh",
            "services/web1/challenge.yaml",
            "services/redis1/Dockerfile",
            "services/redis1/start.sh",
            "services/redis1/changeflag.sh",
            "services/redis1/challenge.yaml",
        ],
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Golden snapshot regression")
    parser.add_argument("--manifest", default=str(MANIFEST), help="snapshot manifest path")
    parser.add_argument("--case", action="append", choices=sorted(CASES), help="case id to run; may be repeated")
    parser.add_argument("--update", action="store_true", help="update manifest with current generated hashes")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_case(case_id: str, out_root: Path) -> dict[str, Any]:
    case = CASES[case_id]
    out_dir = out_root / case_id
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [part.format(out=str(out_dir)) for part in case["command"]]
    proc = subprocess.run(
        cmd,
        cwd=str(case["cwd"]),
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    result: dict[str, Any] = {
        "id": case_id,
        "description": case["description"],
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "files": {},
        "missing": [],
        "stdout": proc.stdout[-4000:],
        "stderr": proc.stderr[-4000:],
    }
    if proc.returncode != 0:
        return result
    for rel in case["files"]:
        path = out_dir / rel
        if path.is_file():
            result["files"][rel] = sha256_file(path)
        else:
            result["missing"].append(rel)
            result["ok"] = False
    return result


def load_manifest(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def build_manifest(results: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cases": {
            item["id"]: {
                "description": item["description"],
                "files": item["files"],
            }
            for item in results
            if item["ok"]
        },
    }


def compare_results(results: list[dict[str, Any]], manifest: dict[str, Any]) -> dict[str, Any]:
    expected_cases = manifest.get("cases") if isinstance(manifest.get("cases"), dict) else {}
    failures: list[dict[str, Any]] = []
    for item in results:
        case_id = item["id"]
        expected = expected_cases.get(case_id)
        if not item["ok"]:
            failures.append({"case": case_id, "reason": "render_failed_or_missing_output", "detail": item})
            continue
        if not isinstance(expected, dict):
            failures.append({"case": case_id, "reason": "missing_case_in_manifest"})
            continue
        expected_files = expected.get("files") if isinstance(expected.get("files"), dict) else {}
        actual_files = item["files"]
        for rel, digest in actual_files.items():
            if expected_files.get(rel) != digest:
                failures.append(
                    {
                        "case": case_id,
                        "file": rel,
                        "reason": "hash_mismatch",
                        "expected": expected_files.get(rel),
                        "actual": digest,
                    }
                )
        for rel in sorted(set(expected_files) - set(actual_files)):
            failures.append({"case": case_id, "file": rel, "reason": "expected_file_missing_from_actual"})
    return {"ok": not failures, "failures": failures}


def main() -> int:
    args = parse_args()
    manifest_path = Path(args.manifest).resolve()
    selected = args.case or sorted(CASES)
    with tempfile.TemporaryDirectory(prefix="ctf-golden-") as td:
        out_root = Path(td)
        results = [run_case(case_id, out_root) for case_id in selected]

    payload: dict[str, Any] = {
        "ok": True,
        "manifest": str(manifest_path),
        "updated": False,
        "results": results,
    }
    if args.update:
        failed = [item for item in results if not item["ok"]]
        if failed:
            payload["ok"] = False
            payload["error"] = "cannot update manifest because at least one case failed"
        else:
            manifest_path.parent.mkdir(parents=True, exist_ok=True)
            manifest_path.write_text(json.dumps(build_manifest(results), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            payload["updated"] = True
    else:
        manifest = load_manifest(manifest_path)
        if not manifest:
            payload["ok"] = False
            payload["error"] = "missing snapshot manifest; run with --update after reviewing outputs"
        else:
            payload.update(compare_results(results, manifest))

    if args.format == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        status = "OK" if payload.get("ok") else "FAIL"
        print(f"Golden snapshot: {status}")
        print(f"- manifest: {manifest_path}")
        print(f"- cases: {len(results)}")
        if payload.get("updated"):
            print("- updated: true")
        for item in results:
            item_status = "OK" if item["ok"] else f"FAIL({item['returncode']})"
            print(f"  - {item['id']}: {item_status}")
        for failure in payload.get("failures", []):
            print(f"[FAIL] {failure}", file=sys.stderr)
        if payload.get("error"):
            print(f"[ERROR] {payload['error']}", file=sys.stderr)

    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
