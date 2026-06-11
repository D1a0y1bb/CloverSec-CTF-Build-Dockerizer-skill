#!/usr/bin/env python3
"""Verify external asset manifests for Linux-QEMU manual cases."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from utils import ConfigError, ensure_list, load_yaml_file


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify external Linux-QEMU asset manifest")
    parser.add_argument("--manifest", required=True, help="asset_manifest.yaml path")
    parser.add_argument("--base-dir", default="", help="override external case directory")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def emit_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main() -> int:
    args = parse_args()
    manifest_path = Path(args.manifest).expanduser().resolve()

    try:
        data = load_yaml_file(manifest_path)
        if not isinstance(data, dict):
            raise ConfigError("asset manifest root must be an object")
        base_dir_raw = args.base_dir or data.get("external_case_dir")
        if not base_dir_raw:
            raise ConfigError("asset manifest requires external_case_dir or --base-dir")
        base_dir = Path(str(base_dir_raw)).expanduser().resolve()
        assets = ensure_list(data.get("assets"), "assets")
    except ConfigError as exc:
        payload = {
            "ok": False,
            "code": "ASSET_MANIFEST_INVALID",
            "summary": str(exc),
            "manifest": str(manifest_path),
        }
        if args.format == "json":
            emit_json(payload)
        else:
            print(f"[ERROR] {payload['code']}: {payload['summary']}", file=sys.stderr)
        return 2

    results: list[dict[str, Any]] = []
    ok = True
    for asset in assets:
        if not isinstance(asset, dict):
            results.append({"ok": False, "code": "ASSET_ENTRY_INVALID", "summary": "asset entry must be an object"})
            ok = False
            continue
        rel = str(asset.get("path", "")).strip()
        role = str(asset.get("role", rel or "asset"))
        expected_size = asset.get("size_bytes")
        expected_sha256 = str(asset.get("sha256", "")).strip().lower()
        if not rel:
            results.append({"ok": False, "role": role, "code": "ASSET_PATH_MISSING", "summary": "path is required"})
            ok = False
            continue

        path = (base_dir / rel).resolve()
        item: dict[str, Any] = {
            "ok": True,
            "role": role,
            "path": rel,
            "absolute_path": str(path),
            "code": "ASSET_OK",
        }
        if not path.is_file():
            item.update({"ok": False, "code": "ASSET_MISSING", "summary": "file not found"})
            results.append(item)
            ok = False
            continue

        actual_size = path.stat().st_size
        item["size_bytes"] = actual_size
        if expected_size is not None and int(expected_size) != actual_size:
            item.update({
                "ok": False,
                "code": "ASSET_SIZE_MISMATCH",
                "expected_size_bytes": int(expected_size),
                "summary": "file size mismatch",
            })
            results.append(item)
            ok = False
            continue

        if expected_sha256:
            actual_sha256 = sha256_file(path)
            item["sha256"] = actual_sha256
            if actual_sha256 != expected_sha256:
                item.update({
                    "ok": False,
                    "code": "ASSET_SHA256_MISMATCH",
                    "expected_sha256": expected_sha256,
                    "summary": "sha256 mismatch",
                })
                ok = False
        results.append(item)

    payload = {
        "ok": ok,
        "code": "ASSET_MANIFEST_PASSED" if ok else "ASSET_MANIFEST_FAILED",
        "manifest": str(manifest_path),
        "base_dir": str(base_dir),
        "assets": results,
    }
    if args.format == "json":
        emit_json(payload)
    else:
        for item in results:
            status = "OK" if item.get("ok") else "FAIL"
            print(f"[{status}] {item.get('role')}: {item.get('path')} ({item.get('code')})")
        if ok:
            print("[OK] asset manifest passed")
        else:
            print("[FAIL] asset manifest failed", file=sys.stderr)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
