#!/usr/bin/env python3
"""Validate Build_test real cases against expected audit and contract results."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

try:
    import yaml
except ImportError:  # pragma: no cover - exercised only on incomplete hosts.
    yaml = None


REPO_ROOT = Path(__file__).resolve().parents[1]
BUILD_TEST_DIR = REPO_ROOT / "Build_test"
DEFAULT_CASES_FILE = BUILD_TEST_DIR / "cases.yaml"
AUDIT_SCRIPT = REPO_ROOT / "src/CloverSec-CTF-Build-Dockerizer/scripts/audit_input.py"
VALIDATE_SCRIPT = REPO_ROOT / "src/CloverSec-CTF-Build-Dockerizer/scripts/validate.sh"


def _run(cmd: List[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _tail(text: str, lines: int = 30) -> List[str]:
    merged = text.strip().splitlines()
    return merged[-lines:]


def _load_cases(path: Path) -> List[Dict[str, Any]]:
    if yaml is None:
        raise RuntimeError("PyYAML is required. Install with: pip3 install pyyaml")
    if not path.exists():
        raise RuntimeError(f"cases file not found: {path}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    cases = raw.get("cases", [])
    if not isinstance(cases, list):
        raise RuntimeError("Build_test cases.yaml must contain a cases list")
    return cases


def _case_path(case: Dict[str, Any]) -> Path:
    raw_path = str(case.get("path", "")).strip()
    if not raw_path:
        raise RuntimeError(f"case {case.get('id', '<missing>')} has empty path")
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return BUILD_TEST_DIR / path


def _audit_case(case_dir: Path) -> Tuple[Dict[str, Any], subprocess.CompletedProcess[str]]:
    cmd = [
        sys.executable,
        str(AUDIT_SCRIPT),
        "--project-dir",
        str(case_dir),
        "--format",
        "json",
    ]
    challenge = case_dir / "challenge.yaml"
    if challenge.exists():
        cmd.extend(["--config", str(challenge)])
    proc = _run(cmd)
    data: Dict[str, Any] = {}
    if proc.returncode == 0:
        data = json.loads(proc.stdout)
    return data, proc


def _validate_contract(case_dir: Path, summary_path: Path) -> subprocess.CompletedProcess[str]:
    return _run(
        [
            "bash",
            str(VALIDATE_SCRIPT),
            "--json-summary",
            str(summary_path),
            str(case_dir / "Dockerfile"),
            str(case_dir / "start.sh"),
            str(case_dir / "challenge.yaml"),
        ]
    )


def _compare_audit(expected: Dict[str, Any], actual: Dict[str, Any]) -> Tuple[bool, List[Dict[str, Any]]]:
    mismatches = []
    for key, expected_value in expected.items():
        actual_value = actual.get(key)
        if actual_value != expected_value:
            mismatches.append({"field": key, "expected": expected_value, "actual": actual_value})
    return not mismatches, mismatches


def _contract_files_ready(case_dir: Path) -> bool:
    return all((case_dir / name).exists() for name in ("Dockerfile", "start.sh", "challenge.yaml"))


def validate_case(case: Dict[str, Any]) -> Dict[str, Any]:
    case_id = str(case.get("id", "")).strip()
    if not case_id:
        return {"id": "<missing>", "ok": False, "error": "case id is required"}

    case_dir = _case_path(case)
    result: Dict[str, Any] = {
        "id": case_id,
        "title": case.get("title", ""),
        "path": str(case_dir.relative_to(REPO_ROOT) if case_dir.is_relative_to(REPO_ROOT) else case_dir),
        "ok": False,
    }

    if not case_dir.exists():
        result["error"] = f"case path not found: {case_dir}"
        return result

    audit_actual, audit_proc = _audit_case(case_dir)
    audit_result: Dict[str, Any] = {
        "returncode": audit_proc.returncode,
        "ok": False,
        "expected": case.get("audit", {}),
        "actual": audit_actual,
        "mismatches": [],
        "stderr_tail": _tail(audit_proc.stderr),
    }
    if audit_proc.returncode == 0:
        audit_ok, mismatches = _compare_audit(case.get("audit", {}), audit_actual)
        audit_result["ok"] = audit_ok
        audit_result["mismatches"] = mismatches
    result["audit"] = audit_result

    contract_spec = case.get("contract", {}) or {}
    contract_result: Dict[str, Any] = {
        "enabled": bool(contract_spec.get("enabled", False)),
        "expected": contract_spec.get("expected", "skipped"),
        "reason": contract_spec.get("reason", ""),
        "ok": True,
        "actual": "skipped",
    }

    if contract_result["enabled"]:
        if not _contract_files_ready(case_dir):
            contract_result.update(
                {
                    "ok": False,
                    "actual": "missing_files",
                    "returncode": None,
                    "stdout_tail": [],
                    "stderr_tail": [],
                }
            )
        else:
            with tempfile.TemporaryDirectory(prefix="ctf-build-test-") as tmp:
                summary_path = Path(tmp) / "validate-summary.json"
                proc = _validate_contract(case_dir, summary_path)
                summary_data: Dict[str, Any] = {}
                if summary_path.exists():
                    try:
                        summary_data = json.loads(summary_path.read_text(encoding="utf-8"))
                    except json.JSONDecodeError:
                        summary_data = {"parse_error": "invalid json summary"}
            actual = "pass" if proc.returncode == 0 else "fail"
            expected = str(contract_result["expected"])
            actual_code = str(summary_data.get("code") or "")
            expected_code = str(contract_spec.get("expected_code") or "").strip()
            code_ok = True if not expected_code else actual_code == expected_code
            contract_result.update(
                {
                    "actual": actual,
                    "actual_code": actual_code,
                    "expected_code": expected_code,
                    "returncode": proc.returncode,
                    "summary": summary_data,
                    "stdout_tail": _tail(proc.stdout),
                    "stderr_tail": _tail(proc.stderr),
                    "ok": actual == expected and code_ok,
                }
            )
    result["contract"] = contract_result
    result["ok"] = bool(audit_result["ok"] and contract_result["ok"])
    return result


def _filter_cases(cases: Iterable[Dict[str, Any]], wanted: List[str]) -> List[Dict[str, Any]]:
    selected = list(cases)
    if not wanted:
        return selected
    by_id = {str(case.get("id", "")): case for case in selected}
    missing = [case_id for case_id in wanted if case_id not in by_id]
    if missing:
        raise RuntimeError(f"unknown case id(s): {', '.join(missing)}")
    return [by_id[case_id] for case_id in wanted]


def _summary(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    failed = [item for item in results if not item.get("ok")]
    contract_skipped = [
        item
        for item in results
        if not item.get("contract", {}).get("enabled", False)
    ]
    return {
        "ok": not failed,
        "total": len(results),
        "passed": len(results) - len(failed),
        "failed": len(failed),
        "skipped": 0,
        "contract_skipped": len(contract_skipped),
        "cases": results,
    }


def emit_text(summary: Dict[str, Any]) -> None:
    print("Build_test regression")
    for item in summary["cases"]:
        status = "OK" if item.get("ok") else "FAIL"
        audit = item.get("audit", {})
        contract = item.get("contract", {})
        print(
            f"[{status}] {item['id']} "
            f"audit={audit.get('ok')} "
            f"contract={contract.get('actual')} expected={contract.get('expected')}"
        )
        if not item.get("ok"):
            for mismatch in audit.get("mismatches", []):
                print(
                    "  audit mismatch: "
                    f"{mismatch['field']} expected={mismatch['expected']} actual={mismatch['actual']}"
                )
            if not contract.get("ok", True):
                print(
                    "  contract mismatch: "
                    f"expected={contract.get('expected')} actual={contract.get('actual')}"
                )
    print(
        "Summary: "
        f"total={summary['total']} passed={summary['passed']} "
        f"failed={summary['failed']} contract_skipped={summary['contract_skipped']}"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Build_test real cases")
    parser.add_argument("--cases-file", default=str(DEFAULT_CASES_FILE))
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--case", dest="case_ids", action="append", default=[])
    parser.add_argument("--fail-fast", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        cases = _filter_cases(_load_cases(Path(args.cases_file)), args.case_ids)
        results: List[Dict[str, Any]] = []
        for case in cases:
            result = validate_case(case)
            results.append(result)
            if args.fail_fast and not result.get("ok"):
                break
        summary = _summary(results)
    except Exception as exc:
        summary = {
            "ok": False,
            "total": 0,
            "passed": 0,
            "failed": 1,
            "skipped": 0,
            "contract_skipped": 0,
            "error": str(exc),
            "cases": [],
        }

    if args.format == "json":
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        if "error" in summary:
            print(f"[FAIL] {summary['error']}", file=sys.stderr)
        else:
            emit_text(summary)
    return 0 if summary.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
