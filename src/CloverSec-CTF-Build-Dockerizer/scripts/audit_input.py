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


_PWN_FLAG_HINT_RE = re.compile(
    r"""(?P<quoted>["'](?P<qpath>(?:\.?/)?(?:flag[0-9]+|flag\.txt)|/home/ctf/flag(?:[0-9]+)?|/flag(?:[0-9]+|\.txt)?)["'])"""
    r"""|(?P<bare>\bflag[0-9]+\b|\bflag\.txt\b)""",
    re.IGNORECASE,
)
_TEXT_SUFFIXES = {
    "",
    ".c",
    ".cc",
    ".cpp",
    ".cxx",
    ".h",
    ".hpp",
    ".py",
    ".php",
    ".js",
    ".ts",
    ".go",
    ".rs",
    ".java",
    ".sh",
    ".txt",
    ".md",
    ".conf",
    ".service",
}
_SKIP_DIRS = {
    ".git",
    ".ctfbuild",
    "__pycache__",
    "node_modules",
    "vendor",
    "dist",
    "build",
    ".venv",
    "venv",
}
_PYTHON_DEP_FILES = {"requirements.txt", "pyproject.toml", "Pipfile", "setup.py", "setup.cfg", "poetry.lock"}
_PYTHON_WEB_IMPORTS = {"flask", "fastapi", "django", "uvicorn", "gunicorn"}
_COMMON_THIRD_PARTY_IMPORTS = {
    "aiohttp",
    "bs4",
    "click",
    "cryptography",
    "cv2",
    "dotenv",
    "flask",
    "gunicorn",
    "jinja2",
    "jwt",
    "matplotlib",
    "numpy",
    "pandas",
    "PIL",
    "pwn",
    "requests",
    "scipy",
    "sqlalchemy",
    "torch",
    "uvicorn",
    "werkzeug",
    "yaml",
}
_IMPORT_RE = re.compile(r"^\s*(?:import\s+([A-Za-z_][A-Za-z0-9_]*)|from\s+([A-Za-z_][A-Za-z0-9_]*)\s+import)\b", re.MULTILINE)
_RENDER_TEMPLATE_RE = re.compile(r"render_template\(\s*[\"']([^\"']+)[\"']")
_FLAG_ENV_RE = re.compile(r"(?:os\.)?environ(?:\.get)?\(\s*[\"']FLAG[\"']|(?:os\.)?environ\[\s*[\"']FLAG[\"']|os\.getenv\(\s*[\"']FLAG[\"']")
_APP_RUN_RE = re.compile(r"\b(app|application)\.run\s*\(")
_MAIN_GUARD_RE = re.compile(r"__name__\s*==\s*[\"']__main__[\"']")


def _normalise_flag_hint(raw: str) -> str:
    value = raw.strip().strip("\"'")
    if value.startswith("./"):
        value = value[2:]
    return value


def _scan_pwn_flag_hints(project_dir: Path) -> List[Dict[str, Any]]:
    hints: List[Dict[str, Any]] = []
    seen: set[tuple[str, str, int]] = set()
    scanned = 0
    for path in project_dir.rglob("*"):
        if scanned >= 120:
            break
        if not path.is_file():
            continue
        if any(part in _SKIP_DIRS for part in path.relative_to(project_dir).parts):
            continue
        if path.name in {"challenge.yaml", "challenge.yml"}:
            continue
        if path.suffix.lower() not in _TEXT_SUFFIXES and path.name not in {"Dockerfile", "Makefile"}:
            continue
        try:
            if path.stat().st_size > 256 * 1024:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        scanned += 1
        for line_no, line in enumerate(text.splitlines(), start=1):
            for match in _PWN_FLAG_HINT_RE.finditer(line):
                raw = match.group("qpath") or match.group("bare") or ""
                flag_path = _normalise_flag_hint(raw)
                key = (str(path), flag_path, line_no)
                if not flag_path or key in seen:
                    continue
                seen.add(key)
                hints.append(
                    {
                        "path": flag_path,
                        "file": _rel_or_empty(path, project_dir),
                        "line": line_no,
                        "evidence": line.strip()[:180],
                    }
                )
                if len(hints) >= 20:
                    return hints
    return hints


def _iter_python_files(project_dir: Path) -> List[Path]:
    files: List[Path] = []
    for path in project_dir.rglob("*.py"):
        try:
            rel_parts = path.relative_to(project_dir).parts
        except ValueError:
            continue
        if any(part in _SKIP_DIRS for part in rel_parts):
            continue
        try:
            if path.stat().st_size > 512 * 1024:
                continue
        except OSError:
            continue
        files.append(path)
        if len(files) >= 160:
            break
    return files


def _has_python_dependency_file(project_dir: Path) -> bool:
    return any((project_dir / name).is_file() for name in _PYTHON_DEP_FILES)


def _module_exists(project_dir: Path, module: str) -> bool:
    if (project_dir / f"{module}.py").is_file():
        return True
    package_init = project_dir / module / "__init__.py"
    return package_init.is_file()


def _stdlib_modules() -> set[str]:
    return set(getattr(sys, "stdlib_module_names", set()))


def _scan_python_source_findings(project_dir: Path, stack_id: str, start_cmd: str) -> List[Dict[str, Any]]:
    python_files = _iter_python_files(project_dir)
    if not python_files:
        return []
    if stack_id and stack_id != "python" and not (project_dir / "app.py").is_file():
        return []

    findings: List[Dict[str, Any]] = []
    seen_codes: set[tuple[str, str]] = set()
    imports: set[str] = set()
    stdlib = _stdlib_modules()

    def add(code: str, summary: str, *, file: str = "", hint: str = "") -> None:
        key = (code, file or summary)
        if key in seen_codes:
            return
        seen_codes.add(key)
        findings.append({"code": code, "summary": summary, "file": file, "hint": hint})

    for path in python_files:
        rel = _rel_or_empty(path, project_dir)
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for match in _IMPORT_RE.finditer(text):
            module = match.group(1) or match.group(2) or ""
            if module:
                imports.add(module)
                if (
                    module not in stdlib
                    and module not in _COMMON_THIRD_PARTY_IMPORTS
                    and not _module_exists(project_dir, module)
                ):
                    add(
                        "PYTHON_LOCAL_IMPORT_MISSING",
                        f"Python 源码引用 `{module}`，但项目目录中没有 `{module}.py` 或 `{module}/__init__.py`。",
                        file=rel,
                        hint="补齐本地模块，或在依赖文件中声明对应第三方包并人工确认启动方式。",
                    )
        for template in _RENDER_TEMPLATE_RE.findall(text):
            candidates = [project_dir / "templates" / template, path.parent / "templates" / template]
            if not any(candidate.is_file() for candidate in candidates):
                add(
                    "FLASK_TEMPLATE_MISSING",
                    f"Flask render_template 引用了缺失模板 `{template}`。",
                    file=rel,
                    hint=f"补齐 templates/{template}，或确认题目运行时模板路径。",
                )
        if _FLAG_ENV_RE.search(text):
            add(
                "FLAG_ENV_NEEDS_PLATFORM_SYNC",
                "源码读取 `FLAG` 环境变量；平台动态 flag 默认写文件，不会自动更新已启动进程环境变量。",
                file=rel,
                hint="确认题目是否改为读取 /flag，或补充平台调用 /changeflag.sh 后业务可读到动态 flag 的方案。",
            )

    if imports & _PYTHON_WEB_IMPORTS and not _has_python_dependency_file(project_dir):
        add(
            "PYTHON_DEPENDENCY_DECLARATION_MISSING",
            "检测到 Python Web 依赖 import，但没有 requirements.txt/pyproject.toml/Pipfile/setup.py。",
            file="",
            hint="补充依赖声明，避免 Dockerfile 渲染后缺包启动失败。",
        )

    app_py = project_dir / "app.py"
    if app_py.is_file() and start_cmd.strip() == "python app.py":
        app_text = app_py.read_text(encoding="utf-8", errors="ignore")
        if not _APP_RUN_RE.search(app_text) and not _MAIN_GUARD_RE.search(app_text):
            add(
                "FLASK_START_COMMAND_UNCONFIRMED",
                "`python app.py` 缺少明确的 app.run 或 __main__ 启动证据。",
                file="app.py",
                hint="确认真实启动命令，例如 flask run、gunicorn、uvicorn，或在源码中补齐启动入口。",
            )

    return findings


def _configured_flag_paths(challenge_doc: Dict[str, Any], config_proposal: Dict[str, Any]) -> set[str]:
    flag = challenge_doc.get("flag") if isinstance(challenge_doc.get("flag"), dict) else {}
    if not flag and isinstance(config_proposal.get("flag"), dict):
        flag = config_proposal["flag"]
    paths: set[str] = set()
    path_value = flag.get("path")
    if isinstance(path_value, str) and path_value.strip():
        paths.add(path_value.strip())
    sync_paths = flag.get("sync_paths")
    if isinstance(sync_paths, list):
        for item in sync_paths:
            if str(item).strip():
                paths.add(str(item).strip())
    return paths


def _stack_detail_summary(details: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    summary: List[Dict[str, Any]] = []
    for item in details[:5]:
        summary.append(
            {
                "id": item.get("id", ""),
                "score": item.get("score", 0),
                "file_hits": item.get("file_hits", []),
                "dir_hits": item.get("dir_hits", []),
            }
        )
    return summary


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
    explicit_stack = str(challenge_doc.get("stack") or "").strip()
    proposal_stack = str(config_proposal.get("stack") or "").strip()
    guessed_stack = str(stack_guess.get("id") or "").strip()
    if explicit_stack:
        stack_id = explicit_stack
        stack_source = "challenge.yaml"
    elif proposal_stack:
        stack_id = proposal_stack
        stack_source = "config_proposal"
    elif guessed_stack:
        stack_id = guessed_stack
        stack_source = "stack_guess"
    else:
        stack_id = detected_id or ""
        stack_source = "detected" if detected_id else "unknown"
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

    if explicit_stack and detected_id and detected_id != explicit_stack and confidence >= 0.4:
        findings.append(
            _finding(
                "INTAKE_DETECTED_STACK_DIFFERS",
                f"challenge.yaml 明确声明 {explicit_stack}，目录探测提示为 {detected_id}。",
                level="info",
                file=_rel_or_empty(challenge_path, project_dir) if challenge_path and challenge_path.exists() else "",
                hint="明确配置优先；探测结果仅作为复核提示。",
            )
        )
    elif challenge_doc and detected_id and stack_id and detected_id != stack_id and confidence >= 0.4:
        add(
            "INTAKE_STACK_CONFLICT",
            f"配置声明 {stack_id}，目录探测更像 {detected_id}。",
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

    pwn_flag_hints = _scan_pwn_flag_hints(project_dir) if stack_id == "pwn" else []
    if stack_id == "pwn":
        configured_paths = _configured_flag_paths(challenge_doc, config_proposal)
        hint_paths = {item["path"] for item in pwn_flag_hints}
        missing_paths = sorted(
            path
            for path in hint_paths
            if path not in configured_paths
            and f"/home/ctf/{path}" not in configured_paths
            and not (not path.startswith("/") and any(item.endswith(f"/{path}") for item in configured_paths))
        )
        if pwn_flag_hints and missing_paths:
            add(
                "PWN_FLAG_PATH_REVIEW_REQUIRED",
                "源码里发现疑似业务 flag 路径，需要确认 challenge.flag.sync_paths。",
                hint="查看 flag_path_hints，把真实业务读取路径写入 challenge.flag.sync_paths。",
                risk="mixed",
                path="proposal_required",
                verify="rendered",
            )
        elif not pwn_flag_hints:
            add(
                "PWN_FLAG_PATH_CONFIRM_REQUIRED",
                "Pwn 题无法仅靠文件结构确认业务 flag 路径。",
                hint="看源码或 PoC，确认程序读取 /flag、/home/ctf/flag、flag0/flag1 还是其他路径。",
                risk="mixed",
                path="proposal_required",
                verify="rendered",
            )

    for finding in _scan_python_source_findings(project_dir, stack_id, start_cmd):
        add(
            str(finding.get("code") or "PYTHON_SOURCE_REVIEW_REQUIRED"),
            str(finding.get("summary") or "Python 源码需要人工复核。"),
            level="error",
            file=str(finding.get("file") or ""),
            hint=str(finding.get("hint") or ""),
            risk="mixed",
            path="proposal_required",
            support="partial",
            verify="rendered",
        )

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
        "stack_source": stack_source,
        "detected_stack": detected_id,
        "detected_stack_hint": {
            "id": detected_id,
            "confidence": confidence,
            "differs_from_explicit": bool(explicit_stack and detected_id and detected_id != explicit_stack),
            "details": _stack_detail_summary(details),
        },
        "detection_confidence": confidence,
        "explicit_config": {
            "stack": bool(explicit_stack),
            "ports": bool(ports),
            "start": bool(start_cmd),
            "profile": bool(profile),
        },
        "flag_path_hints": pwn_flag_hints,
        "findings": findings,
    }


def proposal_gate_required(audit: Dict[str, Any]) -> bool:
    return bool(audit.get("manual_required")) or audit.get("risk_level") in {"mixed", "dirty", "high_risk"}


def can_auto_proceed(audit: Dict[str, Any]) -> tuple[bool, List[str]]:
    blockers: List[str] = []
    risk_level = str(audit.get("risk_level") or "clean")
    support_level = str(audit.get("support_level") or "supported")
    recommended_path = str(audit.get("recommended_path") or "direct_render")
    finding_codes = {str(item.get("code") or "") for item in audit.get("findings", []) if isinstance(item, dict)}

    if risk_level == "high_risk":
        blockers.append("输入风险等级为 high_risk")
    if support_level == "unsupported":
        blockers.append("当前输入不在自动渲染支持范围")
    if recommended_path in {"scenario_draft", "bundle_recipe", "manual_review"}:
        blockers.append(f"推荐路径为 {recommended_path}，需要人工整理后再生成平台交付件")
    if any(code in finding_codes for code in {"INTAKE_COMPOSE_DETECTED", "INTAKE_VULHUB_LIKE_DETECTED"}):
        blockers.append("检测到 compose/Vulhub-like 多服务结构")
    if "INTAKE_CPANEL_WHM_DETECTED" in finding_codes:
        blockers.append("检测到 cPanel/WHM 控制面板类输入")
    if any(code.startswith("LINUX_QEMU_") for code in finding_codes):
        blockers.append("Linux-QEMU 资产需要人工核对")
    if any(
        code in finding_codes
        for code in {
            "PYTHON_LOCAL_IMPORT_MISSING",
            "FLASK_TEMPLATE_MISSING",
            "PYTHON_DEPENDENCY_DECLARATION_MISSING",
            "FLASK_START_COMMAND_UNCONFIRMED",
            "FLAG_ENV_NEEDS_PLATFORM_SYNC",
        }
    ):
        blockers.append("Python 源码存在缺失材料或启动方式风险")

    return not blockers, blockers


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
