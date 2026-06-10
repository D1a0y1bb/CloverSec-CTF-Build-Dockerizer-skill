#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from result_utils import dump_json
from utils import ConfigError, detect_stack, load_stack_defs, load_yaml_file


SCHEMA_VERSION = "1.0"
SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
DATA_DIR = SKILL_ROOT / "data"

RISK_ORDER = {"clean": 0, "mixed": 1, "dirty": 2, "high_risk": 3}
PATH_ORDER = {
    "direct_render": 0,
    "proposal_required": 1,
    "scenario_draft": 2,
    "bundle_recipe": 3,
    "manual_review": 4,
}
SUPPORT_ORDER = {"supported": 0, "partial": 1, "unsupported": 2}
VERIFY_ORDER = {"static": 0, "rendered": 1, "docker_smoke": 2, "manual": 3}


def _rank_update(current: str, candidate: str, order: Dict[str, int]) -> str:
    return candidate if order[candidate] > order[current] else current


def _finding(
    code: str,
    summary: str,
    *,
    level: str = "warning",
    file: str = "",
    hint: str = "",
    autofixable: bool = False,
) -> Dict[str, Any]:
    return {
        "code": code,
        "level": level,
        "summary": summary,
        "file": file,
        "hint": hint,
        "autofixable": bool(autofixable),
    }


def _has_any(project_dir: Path, names: Iterable[str]) -> Optional[Path]:
    for name in names:
        path = project_dir / name
        if path.exists():
            return path
    return None


def _collect_text(project_dir: Path) -> str:
    snippets: List[str] = []
    candidates = [
        "README.md",
        "readme.md",
        "Dockerfile",
        "docker-compose.yml",
        "docker-compose.yaml",
        "compose.yml",
        "compose.yaml",
        "challenge.yaml",
        "challenge.yml",
        "CONFIG.md",
        "config.md",
        "start.sh",
    ]
    for rel in candidates:
        path = project_dir / rel
        if path.is_file():
            try:
                snippets.append(path.read_text(encoding="utf-8", errors="ignore")[:20000])
            except OSError:
                pass
    return "\n".join(snippets).lower()


def _challenge_from_path(challenge_path: Optional[Path]) -> Dict[str, Any]:
    if not challenge_path:
        return {}
    if not challenge_path.exists():
        return {}
    loaded = load_yaml_file(challenge_path)
    if not isinstance(loaded, dict):
        return {}
    return loaded.get("challenge") if isinstance(loaded.get("challenge"), dict) else loaded


def _normalise_ports(value: Any) -> List[Dict[str, Any]]:
    if not value:
        return []
    if isinstance(value, list):
        ports = []
        for item in value:
            if isinstance(item, dict):
                ports.append(item)
            elif str(item).strip():
                ports.append({"container": str(item).strip()})
        return ports
    if isinstance(value, str) and value.strip():
        return [{"container": value.strip()}]
    if isinstance(value, (int, float)):
        return [{"container": str(int(value))}]
    return []


def _contains_placeholder(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        data = path.read_bytes()[:4096]
    except OSError:
        return False
    text = data.decode("utf-8", errors="ignore").lower()
    return any(marker in text for marker in ("placeholder", "todo", "replace-me", "dummy", "example"))


def _resolve_vm_path(project_dir: Path, vm: Dict[str, Any], key: str) -> Optional[Path]:
    raw = vm.get(key)
    if not isinstance(raw, str) or not raw.strip():
        return None
    path = Path(raw)
    if not path.is_absolute():
        path = project_dir / path
    return path


def _rel_or_empty(path: Optional[Path], root: Path) -> str:
    if not path:
        return ""
    try:
        return str(path.relative_to(root))
    except ValueError:
        return ""


def audit_project(
    project_dir: Path,
    *,
    challenge_path: Optional[Path] = None,
    challenge: Optional[Dict[str, Any]] = None,
    gates: Optional[Dict[str, Any]] = None,
    stack_guess: Optional[Dict[str, Any]] = None,
    config_proposal: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    project_dir = project_dir.resolve()
    gates = gates or {}
    stack_guess = stack_guess or {}
    config_proposal = config_proposal or {}
    challenge_doc = challenge or _challenge_from_path(challenge_path)
    if not config_proposal and challenge_doc:
        config_proposal = challenge_doc

    stack_defs = load_stack_defs(DATA_DIR / "stacks.yaml")
    detected_id, confidence, details = detect_stack(project_dir, stack_defs)
    stack_id = (
        str(challenge_doc.get("stack") or "")
        or str(config_proposal.get("stack") or "")
        or str(stack_guess.get("id") or "")
        or detected_id
        or ""
    )
    profile = challenge_doc.get("profile") or config_proposal.get("profile") or ""
    ports = _normalise_ports(
        challenge_doc.get("ports")
        or challenge_doc.get("expose_ports")
        or config_proposal.get("ports")
        or config_proposal.get("expose_ports")
    )
    start_value = challenge_doc.get("start") or config_proposal.get("start") or ""
    if isinstance(start_value, dict):
        start_cmd = str(start_value.get("cmd") or "")
    else:
        start_cmd = str(start_value or "")
    vm = challenge_doc.get("vm") if isinstance(challenge_doc.get("vm"), dict) else {}
    if not vm and isinstance(config_proposal.get("vm"), dict):
        vm = config_proposal["vm"]

    findings: List[Dict[str, Any]] = []
    risk_level = "clean"
    recommended_path = "direct_render"
    support_level = "supported"
    verification_level = "static"
    manual_required = False

    def add(
        code: str,
        summary: str,
        *,
        level: str = "warning",
        file: str = "",
        hint: str = "",
        autofixable: bool = False,
        risk: str = "mixed",
        path: str = "proposal_required",
        support: str = "partial",
        verify: str = "rendered",
        manual: bool = True,
    ) -> None:
        nonlocal risk_level, recommended_path, support_level, verification_level, manual_required
        findings.append(_finding(code, summary, level=level, file=file, hint=hint, autofixable=autofixable))
        risk_level = _rank_update(risk_level, risk, RISK_ORDER)
        recommended_path = _rank_update(recommended_path, path, PATH_ORDER)
        support_level = _rank_update(support_level, support, SUPPORT_ORDER)
        verification_level = _rank_update(verification_level, verify, VERIFY_ORDER)
        manual_required = manual_required or manual

    compose_path = _has_any(project_dir, ("docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"))
    if compose_path:
        add(
            "INTAKE_COMPOSE_DETECTED",
            "发现 compose 文件，应先转换为 Scenario 草案再拆分服务契约。",
            file=_rel_or_empty(compose_path, project_dir),
            path="scenario_draft",
            verify="manual",
        )

    dockerfile = project_dir / "Dockerfile"
    if dockerfile.exists() and not challenge_doc:
        add(
            "INTAKE_EXISTING_DOCKERFILE",
            "存在旧 Dockerfile 且没有明确 challenge.yaml，渲染前需要确认是否覆盖原交付物。",
            file="Dockerfile",
            risk="dirty",
            path="manual_review",
            verify="manual",
        )

    strong_hits = [item for item in details if item.get("score", 0) >= 3]
    strong_ids = sorted({item.get("id") for item in strong_hits if item.get("id")})
    if len(strong_ids) > 1 and not challenge_doc.get("stack"):
        add(
            "INTAKE_MULTI_STACK_DETECTED",
            f"同时命中多个技术栈：{', '.join(strong_ids)}。",
            hint="通过 proposal 或 challenge.yaml 明确 stack/profile/start/ports。",
            risk="mixed",
        )

    if challenge_doc and detected_id and stack_id and detected_id != stack_id and confidence >= 0.4:
        add(
            "INTAKE_STACK_CONFLICT",
            f"challenge.yaml 声明 {stack_id}，目录探测更像 {detected_id}。",
            file=_rel_or_empty(challenge_path, project_dir) if challenge_path and challenge_path.exists() else "",
            hint="确认 stack 是否按题目真实运行方式填写。",
            risk="mixed",
        )

    if gates and any(bool(value) for value in gates.values()):
        add(
            "INTAKE_DERIVE_GATES_TRUE",
            "derive 阶段仍有字段需要确认。",
            hint="执行 workflow.py propose 后人工接受 proposal。",
            risk="mixed",
        )

    if not ports:
        add(
            "INTAKE_PORT_UNCONFIRMED",
            "没有明确容器端口。",
            hint="在 challenge.yaml ports[] 中声明 container/expose 字段。",
            autofixable=True,
            risk="mixed",
        )

    if not start_cmd and stack_id not in {"static", "linux-qemu"}:
        add(
            "INTAKE_START_UNCONFIRMED",
            "没有明确启动命令。",
            hint="在 challenge.yaml start 字段声明启动命令。",
            autofixable=True,
            risk="mixed",
        )

    text = _collect_text(project_dir)
    if re.search(r"\b(cpanel|whm|cpaneld|whostmgr|cpanel\.net)\b", text):
        add(
            "INTAKE_CPANEL_WHM_DETECTED",
            "发现 cPanel/WHM 相关关键词，默认按 bundle/recipe 或人工方案处理。",
            hint="该类环境通常不是 linux-qemu 内核题，应避免误选 linux-qemu。",
            risk="mixed",
            path="bundle_recipe",
            verify="manual",
        )

    if re.search(r"\bvulhub\b|docker-compose\.yml|docker compose", text):
        add(
            "INTAKE_VULHUB_LIKE_DETECTED",
            "发现 Vulhub/compose 风格线索，建议走 Scenario 草案。",
            path="scenario_draft",
            verify="manual",
        )

    if stack_id == "linux-qemu" or profile == "baseunit-linux-qemu":
        required = {
            "kernel": "LINUX_QEMU_KERNEL_MISSING",
            "rootfs": "LINUX_QEMU_ROOTFS_MISSING",
        }
        optional = {"initrd": "LINUX_QEMU_INITRD_MISSING"}
        for key, code in required.items():
            path = _resolve_vm_path(project_dir, vm, key)
            if not path or not path.exists():
                add(
                    code,
                    f"linux-qemu 缺少 VM 资产：{key}。",
                    file=_rel_or_empty(path, project_dir),
                    risk="high_risk",
                    path="manual_review",
                    support="unsupported",
                    verify="manual",
                )
            elif _contains_placeholder(path):
                add(
                    "LINUX_QEMU_PLACEHOLDER_ASSET",
                    f"linux-qemu VM 资产 {key} 含占位文本。",
                    file=_rel_or_empty(path, project_dir),
                    risk="high_risk",
                    path="manual_review",
                    support="unsupported",
                    verify="manual",
                )
        for key, code in optional.items():
            path = _resolve_vm_path(project_dir, vm, key)
            if path and path.exists() and _contains_placeholder(path):
                add(
                    code.replace("_MISSING", "_PLACEHOLDER"),
                    f"linux-qemu VM 资产 {key} 含占位文本。",
                    file=_rel_or_empty(path, project_dir),
                    risk="high_risk",
                    path="manual_review",
                    support="unsupported",
                    verify="manual",
                )
        verification_level = _rank_update(verification_level, "docker_smoke", VERIFY_ORDER)

    return {
        "schema_version": SCHEMA_VERSION,
        "project_dir": str(project_dir),
        "risk_level": risk_level,
        "recommended_path": recommended_path,
        "support_level": support_level,
        "verification_level": verification_level,
        "manual_required": bool(manual_required),
        "gates": gates,
        "stack_id": stack_id,
        "detected_stack": detected_id,
        "detection_confidence": confidence,
        "findings": findings,
    }


def proposal_gate_required(audit: Dict[str, Any]) -> bool:
    return bool(audit.get("manual_required")) or audit.get("risk_level") in {"mixed", "dirty", "high_risk"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit CTF challenge input before rendering.")
    parser.add_argument("--project-dir", default=".", help="Challenge project directory.")
    parser.add_argument("--config", help="Optional challenge.yaml path.")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_dir = Path(args.project_dir)
    challenge_path = Path(args.config) if args.config else None
    try:
        audit = audit_project(project_dir, challenge_path=challenge_path)
    except ConfigError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2
    if args.format == "json":
        print(dump_json(audit, pretty=True))
    else:
        print(f"risk_level: {audit['risk_level']}")
        print(f"recommended_path: {audit['recommended_path']}")
        print(f"support_level: {audit['support_level']}")
        print(f"verification_level: {audit['verification_level']}")
        print(f"manual_required: {str(audit['manual_required']).lower()}")
        for finding in audit["findings"]:
            print(f"- {finding['code']}: {finding['summary']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
