#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict


def structured_error(
    stage: str,
    code: str,
    summary: str,
    *,
    level: str = "error",
    file: str = "",
    hint: str = "",
    autofixable: bool = False,
    support_level: str = "unknown",
) -> Dict[str, Any]:
    return {
        "ok": False,
        "stage": stage,
        "code": code,
        "level": level,
        "summary": summary,
        "file": file,
        "hint": hint,
        "autofixable": bool(autofixable),
        "support_level": support_level,
    }


def structured_ok(stage: str, **extra: Any) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"ok": True, "stage": stage}
    payload.update(extra)
    return payload


def dump_json(payload: Dict[str, Any], *, pretty: bool = False) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2 if pretty else None, sort_keys=pretty)


def write_json(path: Path, payload: Dict[str, Any], *, pretty: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dump_json(payload, pretty=pretty) + "\n", encoding="utf-8")


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical_json_sha256(payload: Dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256_text(raw)
