#!/usr/bin/env python3
"""Evidence-first CTF delivery workflow.

This command is intentionally separate from the legacy template renderer.
It preserves existing delivery files, uses direct-exec Flag injection by
default, and reports static, build, runtime and business evidence separately.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tarfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from contract import normalize_contract  # noqa: E402


IGNORED_NAMES = {
    ".git",
    ".ctfbuild",
    ".DS_Store",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    "dist",
    "题目手册",
    "附件",
}
IGNORED_SCAN_FILES = {"delivery-manifest.json", "FLAG_UPDATE.md", "VERIFY.md"}
PATH_RE = re.compile(r"(?<![A-Za-z0-9_])/(?:home/ctf/|var/www/html/|challenge/|data/)?[A-Za-z0-9_.@+/-]*(?:flag|secret)[A-Za-z0-9_.@+/-]*")
FROM_RE = re.compile(r"^\s*FROM(?:\s+--platform=\S+)?\s+(\S+)", re.I)
WORKDIR_RE = re.compile(r"^\s*WORKDIR\s+(\S+)", re.I)
EXPOSE_RE = re.compile(r"^\s*EXPOSE\s+(.+)$", re.I)
CMD_RE = re.compile(r"^\s*(CMD|ENTRYPOINT)\s+(.+)$", re.I)


def yaml_load(path: Path) -> Dict[str, Any]:
    try:
        import yaml
    except ModuleNotFoundError as exc:
        raise RuntimeError("缺少 PyYAML。请先执行：python3 -m pip install -r scripts/requirements.txt") from exc
    if not path.exists():
        return {}
    raw = yaml.safe_load(path.read_text(encoding="utf-8", errors="replace")) or {}
    return raw if isinstance(raw, dict) else {}


def yaml_dump(data: Dict[str, Any], path: Path) -> None:
    try:
        import yaml
    except ModuleNotFoundError as exc:
        raise RuntimeError("缺少 PyYAML。请先执行：python3 -m pip install -r scripts/requirements.txt") from exc
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")


def materialize_contract_config(path: Path, contract: Dict[str, Any]) -> None:
    """Write normalized contract facts into the staged challenge config."""
    raw = yaml_load(path)
    challenge = raw.get("challenge") if isinstance(raw.get("challenge"), dict) else raw
    flag = challenge.get("flag") if isinstance(challenge.get("flag"), dict) else {}
    platform = challenge.get("platform") if isinstance(challenge.get("platform"), dict) else {}
    normalized_flag = contract["flag"]
    flag["mode"] = normalized_flag["mode"]
    flag["path"] = normalized_flag["path"]
    flag["initial_file"] = bool(normalized_flag["initial_file"])
    flag["permission"] = normalized_flag["permission"]
    flag["sync_paths"] = list(normalized_flag["sync_paths"])
    if normalized_flag.get("update"):
        flag["update"] = normalized_flag["update"]
    else:
        flag.pop("update", None)
    challenge["flag"] = flag
    platform["contract"] = contract["contract"]
    platform["entrypoint"] = contract["entrypoint"]
    platform["require_bash"] = bool(contract["require_bash"])
    challenge["platform"] = platform
    if "challenge" in raw and isinstance(raw.get("challenge"), dict):
        raw["challenge"] = challenge
    else:
        raw = challenge
    yaml_dump(raw, path)


def run(cmd: List[str], *, cwd: Path | None = None, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None, text=True, capture_output=True, timeout=timeout)


def find_first(project: Path, names: Iterable[str]) -> Path | None:
    wanted = set(names)
    candidates: List[Path] = []
    for path in project.rglob("*"):
        if not path.is_file() or path.name not in wanted:
            continue
        if any(part in IGNORED_NAMES for part in path.parts):
            continue
        candidates.append(path)
    candidates.sort(key=lambda item: (len(item.relative_to(project).parts), str(item)))
    return candidates[0] if candidates else None


def find_dockerfile(project: Path) -> Path | None:
    return find_first(project, {"Dockerfile", "dockerfile"})


def parse_dockerfile(path: Path | None) -> Dict[str, Any]:
    facts: Dict[str, Any] = {
        "path": str(path) if path else "",
        "base_image": "",
        "workdir": "",
        "ports": [],
        "commands": [],
        "copies": [],
    }
    if not path or not path.exists():
        return facts
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        match = FROM_RE.match(line)
        if match and not facts["base_image"]:
            facts["base_image"] = match.group(1)
        match = WORKDIR_RE.match(line)
        if match:
            facts["workdir"] = match.group(1)
        match = EXPOSE_RE.match(line)
        if match:
            facts["ports"].extend(re.findall(r"\d+", match.group(1)))
        match = CMD_RE.match(line)
        if match:
            facts["commands"].append(match.group(2))
        if line.upper().startswith(("COPY ", "ADD ")):
            facts["copies"].append(line)
    facts["ports"] = list(dict.fromkeys(facts["ports"]))
    return facts


def source_root(project: Path, dockerfile: Path | None) -> Path:
    if (project / "src").is_dir():
        return project / "src"
    if dockerfile and (dockerfile.parent / "src").is_dir():
        return dockerfile.parent / "src"
    return dockerfile.parent if dockerfile else project


def read_challenge(project: Path) -> Tuple[Dict[str, Any], Path | None]:
    config = project / "challenge.yaml"
    if not config.exists():
        config = project / ".ctfbuild" / "challenge.yaml"
    if not config.exists():
        return {}, None
    raw = yaml_load(config)
    challenge = raw.get("challenge") if isinstance(raw.get("challenge"), dict) else raw
    return challenge if isinstance(challenge, dict) else {}, config


def scan_flag_hints(root: Path, limit: int = 250) -> List[Dict[str, Any]]:
    result: List[Dict[str, Any]] = []
    files = 0
    for path in root.rglob("*"):
        if files >= limit:
            break
        if not path.is_file() or path.name in IGNORED_SCAN_FILES or path.stat().st_size > 512 * 1024:
            continue
        if any(part in IGNORED_NAMES for part in path.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        files += 1
        for match in PATH_RE.finditer(text):
            value = match.group(0).rstrip("'\"`);,])")
            if value and value not in {"/flag", "/flag.txt"}:
                result.append({"path": str(path), "value": value})
    seen = set()
    unique = []
    for item in result:
        key = (item["path"], item["value"])
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique[:100]


def infer_flag_path(challenge: Dict[str, Any], docker_facts: Dict[str, Any], hints: List[Dict[str, Any]]) -> Tuple[str, str]:
    flag_cfg = challenge.get("flag") if isinstance(challenge.get("flag"), dict) else {}
    explicit = str(flag_cfg.get("path") or "").strip()
    if explicit:
        return explicit, "explicit"
    for copy in docker_facts.get("copies", []):
        match = re.search(r"\s(\/[^\s]+)$", copy)
        if not match:
            continue
        raw_destination = match.group(1)
        destination = raw_destination.rstrip("/")
        source = copy.split()[1] if len(copy.split()) > 1 else ""
        if "flag" in source.lower() or destination.lower().endswith("flag"):
            if raw_destination.endswith("/"):
                destination += "/flag"
            return destination, "dockerfile"
    for item in hints:
        value = str(item.get("value") or "")
        if value.startswith("/") and value not in {"/flag", "/flag.txt"} and "flag" in value.lower():
            return value, "source-hint"
    return "/flag", "default"


def audit(project: Path) -> Dict[str, Any]:
    dockerfile = find_dockerfile(project)
    start = find_first(project, {"start.sh", "entrypoint.sh", "docker-entrypoint.sh"})
    challenge, challenge_path = read_challenge(project)
    facts = parse_dockerfile(dockerfile)
    root = source_root(project, dockerfile)
    start_text = start.read_text(encoding="utf-8", errors="replace") if start else ""
    hints = scan_flag_hints(root)
    contract = normalize_contract(challenge, project)
    inferred_path, inferred_source = infer_flag_path(challenge, facts, hints)
    if inferred_source != "explicit":
        contract["flag"]["path"] = inferred_path
    if not contract["flag"]["initial_file"] and dockerfile:
        for copy in facts.get("copies", []):
            parts = copy.split()
            source = parts[1] if len(parts) > 1 else ""
            source_path = (dockerfile.parent / source).resolve()
            if source.lower().endswith("flag") and source_path.is_file():
                contract["flag"]["initial_file"] = True
                break
    issues: List[Dict[str, Any]] = []
    if not dockerfile:
        issues.append({"code": "DOCKERFILE_MISSING", "status": "unverified", "message": "未发现 Dockerfile"})
    if not start:
        issues.append({"code": "START_MISSING", "status": "unverified", "message": "未发现启动脚本"})
    if start and not re.search(r"(^|\s)exec(\s|$)", start_text):
        issues.append({"code": "START_NO_EXEC", "status": "partial", "message": "start.sh 未发现 exec，需人工确认多进程语义"})
    if not challenge:
        issues.append({"code": "CONFIG_MISSING", "status": "partial", "message": "未发现 challenge.yaml，保留源码事实"})
    if contract["flag"]["mode"] == "direct_exec" and (project / "changeflag.sh").exists():
        issues.append({"code": "LEGACY_HELPER_PRESENT", "status": "partial", "message": "direct-exec 合同下存在旧 changeflag.sh"})
    return {
        "schema_version": "3.0",
        "project": str(project),
        "challenge_config": str(challenge_path) if challenge_path else "",
        "source_root": str(root),
        "delivery_kind": "container" if dockerfile or start else "attachment-only",
        "category": str(challenge.get("category") or "unknown"),
        "dockerfile": facts,
        "start": {"path": str(start) if start else "", "lines": len(start_text.splitlines())},
        "runtime": {
            "base_image": facts["base_image"],
            "workdir": facts["workdir"],
            "ports": facts["ports"],
            "commands": facts["commands"],
        },
        "contract": contract,
        "flag_hints": hints,
        "inference": {"flag_path": inferred_source},
        "issues": issues,
        "status": "passed" if not issues else "partial",
        "verification": "static",
    }


def copy_tree(source: Path, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    for item in source.iterdir():
        if item.name in IGNORED_NAMES or item.name == output.name:
            continue
        target = output / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True, ignore=shutil.ignore_patterns(*IGNORED_NAMES))
        else:
            shutil.copy2(item, target)


def minimal_start(command: str, workdir: str) -> str:
    return "#!/bin/sh\nset -eu\ncd %s\nexec sh -c %s\n" % (shell_quote(workdir), shell_quote(command))


def shell_quote(value: str) -> str:
    import shlex

    return shlex.quote(value)


def minimal_dockerfile(challenge: Dict[str, Any], contract: Dict[str, Any], has_flag: bool, has_requirements: bool = False) -> str:
    base = str(challenge.get("base_image") or "")
    workdir = str(challenge.get("workdir") or "/app")
    ports = challenge.get("expose_ports") or []
    start = challenge.get("start") if isinstance(challenge.get("start"), dict) else {}
    command = str(start.get("cmd") or "")
    if not base or not command:
        raise RuntimeError("缺少 challenge.base_image 或 challenge.start.cmd，无法安全生成最小交付件")
    lines = [f"FROM {base}", "", f"WORKDIR {workdir}", "", "COPY app/ ."]
    if has_requirements:
        lines += ["RUN pip install --no-cache-dir -r requirements.txt"]
    if has_flag:
        flag_path = str(contract["flag"]["path"])
        lines += [f"COPY flag {flag_path}"]
        parent = Path(flag_path).parent.as_posix()
        if parent == "/":
            lines += [f"RUN chmod 444 {flag_path}"]
        else:
            lines += [f"RUN mkdir -p {shell_quote(parent)} && chmod 444 {flag_path}"]
    if ports:
        lines += ["", "EXPOSE " + " ".join(str(item) for item in ports)]
    lines += ["", "COPY start.sh /start.sh", "RUN chmod 555 /start.sh", "", 'CMD ["/start.sh"]', ""]
    return "\n".join(lines)


def helper_script() -> str:
    return """#!/bin/sh
set -eu
target=${FLAG_PATH:-/flag}
flag=${FLAG:-${CTF_FLAG:-${1:-}}}
[ -n "$flag" ] || { echo 'flag value is required' >&2; exit 2; }
mkdir -p "$(dirname "$target")"
printf '%s\\n' "$flag" > "$target"
chmod 444 "$target" 2>/dev/null || true
"""


def compact_entrypoint_text(text: str, kind: str) -> str:
    """Keep executable lines and required headers in delivery entrypoints."""
    lines: List[str] = []
    heredoc_end = ""
    for line in text.splitlines():
        stripped = line.strip()
        if heredoc_end:
            lines.append(line.rstrip())
            if stripped == heredoc_end:
                heredoc_end = ""
            continue
        heredoc = re.search(r"<<-?\s*['\"]?([A-Za-z_][A-Za-z0-9_]*)['\"]?", line)
        if heredoc:
            heredoc_end = heredoc.group(1)
            lines.append(line.rstrip())
            continue
        if stripped.startswith("#"):
            if kind == "docker" and stripped.startswith("# syntax="):
                lines.append(line.rstrip())
            elif kind == "shell" and stripped.startswith("#!"):
                lines.append(line.rstrip())
            continue
        if re.fullmatch(r"\s*:\s*(#.*)?", line):
            continue
        lines.append(line.rstrip())

    compact: List[str] = []
    blank = False
    for line in lines:
        if not line:
            if blank:
                continue
            blank = True
        else:
            blank = False
        compact.append(line)
    return "\n".join(compact).strip() + "\n"


def strip_flag_initialization(text: str) -> str:
    """Remove direct-exec startup blocks that create an empty flag file."""
    lines = text.splitlines()
    output: List[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if re.search(r"\bif\s+\[\[?\s*!\s*-f\s+[^\n]*flag", line):
            block: List[str] = [line]
            index += 1
            if not re.search(r"\bfi\s*$", line):
                while index < len(lines):
                    block.append(lines[index])
                    if re.fullmatch(r"\s*fi\s*", lines[index]):
                        index += 1
                        break
                    index += 1
            if any(re.search(r"\b(touch|mkdir|chmod|chown)\b", item) for item in block):
                continue
            output.extend(block)
            continue
        output.append(line)
        index += 1
    return "\n".join(output)


def strip_legacy_helper_references(output: Path, flag_path: str = "/flag") -> List[str]:
    """Remove helper-only Dockerfile lines during a direct-exec migration."""
    changed: List[str] = []
    dockerfile = output / "Dockerfile"
    if dockerfile.exists():
        text = dockerfile.read_text(encoding="utf-8", errors="replace")
        lines: List[str] = []
        for line in text.splitlines():
            stripped = line.strip()
            if re.search(r"^COPY\s+changeflag\.sh\s+/changeflag\.sh", stripped, re.I):
                continue
            if "changeflag.sh" in line:
                line = re.sub(r"chmod\s+\d+\s+/changeflag\.sh\s*&&\s*", "", line)
                line = re.sub(r"&&\s*chmod\s+\d+\s+/changeflag\.sh", "", line)
                line = re.sub(r"chmod\s+\d+\s+/changeflag\.sh", "", line)
                if not line.strip() or line.strip().startswith("#"):
                    continue
            lines.append(line.rstrip())
        new_text = "\n".join(lines).rstrip() + "\n"
        if new_text != text:
            dockerfile.write_text(new_text, encoding="utf-8")
            changed.append("Dockerfile")
    start = output / "start.sh"
    if start.exists():
        original_text = start.read_text(encoding="utf-8", errors="replace")
        text = original_text
        if flag_path in {"/flag", "/flag.txt"}:
            text = strip_flag_initialization(text)
        new_text = re.sub(
            r"\nif \[\[ -n .*?\]\]; then\n\s*/changeflag\.sh\nfi\n",
            "\n",
            text,
        )
        new_text = re.sub(
            r"\nif \[\[ ! -f [^\n]*flag[^\n]*\]\]; then\n.*?\nfi\n",
            "\n",
            new_text,
            flags=re.S,
        )
        new_text = "\n".join(
            line for line in new_text.splitlines() if "/changeflag.sh" not in line
        ) + "\n"
        new_text = re.sub(r"^.*dynamic_flag_placeholder.*$\n?", "", new_text, flags=re.M)
        new_text = re.sub(
            r"^\s*(chown|chmod)\b[^\n]*\s/flag(?:\.txt)?(?:\s|[;&|]|$)[^\n]*\n?",
            "",
            new_text,
            flags=re.M,
        )
        if new_text != original_text:
            start.write_text(new_text, encoding="utf-8")
            changed.append("start.sh")
    stale = output / "changeflag.sh"
    if stale.is_file():
        stale.unlink()
        changed.append("changeflag.sh")
    return changed


def compact_delivery_entrypoints(output: Path) -> List[str]:
    """Remove narration comments from copied delivery entrypoint files."""
    changed: List[str] = []
    for name, kind in (("Dockerfile", "docker"), ("start.sh", "shell"), ("changeflag.sh", "shell")):
        path = output / name
        if not path.is_file():
            continue
        original = path.read_text(encoding="utf-8", errors="replace")
        compacted = compact_entrypoint_text(original, kind)
        if compacted != original:
            path.write_text(compacted, encoding="utf-8")
            changed.append(name)
    return changed


def update_runbook(contract: Dict[str, Any]) -> str:
    flag = contract["flag"]
    path = flag["path"]
    mode = flag["mode"]
    lines = ["# Flag 更新方式", "", f"mode: `{mode}`", f"target: `{path}`", ""]
    if mode == "direct_exec":
        lines += ["平台启动容器后直接写入目标文件：", "", "```bash", f"docker exec <container> sh -c 'printf \"%s\\n\" \"$1\" > \"$2\"' sh \"$new_flag\" \"{path}\"", "```"]
    elif mode == "file_replace":
        command = str(flag.get("update", {}).get("command") or f"echo \"$new_flag\" > {path}")
        lines += ["按题目手册执行文件更新命令：", "", "```bash", command, "```"]
    elif mode == "database":
        update = flag.get("update", {})
        wait_for = str(update.get("wait_for") or "")
        command = str(update.get("command") or "mysql -e \"UPDATE ...\"")
        if wait_for:
            lines += ["```bash", f"/usr/bin/wait-for-it.sh {wait_for} -- {command}", "```"]
        else:
            lines += ["```bash", command, "```"]
    elif mode == "helper_script":
        lines += ["平台需要显式调用 `/changeflag.sh`。", ""]
    else:
        lines += ["Linux-QEMU 使用 guest rootfs 注入流程。", ""]
    return "\n".join(lines) + "\n"


def manifest_for(directory: Path, audit_result: Dict[str, Any]) -> Dict[str, Any]:
    files: List[Dict[str, Any]] = []
    for path in sorted(directory.rglob("*")):
        if not path.is_file() or path.name == "delivery-manifest.json":
            continue
        data = path.read_bytes()
        files.append({"path": str(path.relative_to(directory)), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    return {"schema_version": "3.0", "status": "prepared", "audit": audit_result, "files": files}


def prepare(project: Path, output: Path, force: bool = False) -> Dict[str, Any]:
    if output.exists() and any(output.iterdir()) and not force:
        raise RuntimeError(f"输出目录非空，请使用 --force: {output}")
    if force and output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)
    audit_result = audit(project)
    prepared_status = str(audit_result.get("status") or "partial")
    challenge, _ = read_challenge(project)
    contract = audit_result["contract"]
    dockerfile = Path(audit_result["dockerfile"]["path"]) if audit_result["dockerfile"].get("path") else None
    build_root = dockerfile.parent if dockerfile else project
    start_cfg = challenge.get("start") if isinstance(challenge.get("start"), dict) else {}
    can_generate_container = bool(str(challenge.get("base_image") or "").strip()) and bool(
        str(start_cfg.get("cmd") or "").strip()
    )

    if not dockerfile and not audit_result["start"].get("path") and not can_generate_container:
        copy_tree(project, output)
        (output / "VERIFY.md").write_text(
            "# Verification\n\n该目录没有服务入口。当前交付类型是 attachment-only。\n",
            encoding="utf-8",
        )
        manifest = manifest_for(output, audit_result)
        manifest["status"] = prepared_status
        (output / "delivery-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return {"status": prepared_status, "output": str(output), "contract": contract, "manifest": str(output / "delivery-manifest.json"), "audit": audit_result}

    if dockerfile:
        copy_tree(build_root, output)
        # A project-level challenge configuration remains useful in the manifest.
        config_path = Path(audit_result["challenge_config"]) if audit_result.get("challenge_config") else None
        if config_path and config_path.is_file() and not (output / "challenge.yaml").exists():
            shutil.copy2(config_path, output / "challenge.yaml")
    else:
        source = project / "src" if (project / "src").is_dir() else project
        app = output / "app"
        shutil.copytree(source, app, dirs_exist_ok=True, ignore=shutil.ignore_patterns(*IGNORED_NAMES))
        has_flag = bool(contract["flag"]["initial_file"] and (project / "flag").is_file())
        (output / "Dockerfile").write_text(
            minimal_dockerfile(challenge, contract, has_flag, (source / "requirements.txt").is_file()),
            encoding="utf-8",
        )
        config_path = Path(audit_result["challenge_config"]) if audit_result.get("challenge_config") else None
        if config_path and config_path.is_file():
            shutil.copy2(config_path, output / "challenge.yaml")

    staged_config = output / "challenge.yaml"
    if staged_config.is_file():
        materialize_contract_config(staged_config, contract)

    start = output / "start.sh"
    if not start.exists():
        command = str(start_cfg.get("cmd") or "")
        if not command:
            raise RuntimeError("缺少 start.sh 和 challenge.start.cmd，无法生成安全启动入口")
        start.write_text(minimal_start(command, str(challenge.get("workdir") or "/app")), encoding="utf-8")
        start.chmod(0o555)

    if (project / "flag").is_file() and contract["flag"]["initial_file"] and not (output / "flag").exists():
        shutil.copy2(project / "flag", output / "flag")
        (output / "flag").chmod(0o444)
    if contract["legacy_helper"]:
        helper = output / "changeflag.sh"
        if not helper.exists():
            helper.write_text(helper_script(), encoding="utf-8")
        helper.chmod(0o555)
    else:
        migrated = strip_legacy_helper_references(output, str(contract["flag"]["path"]))
        if migrated:
            audit_result.setdefault("migrations", []).extend(migrated)
    compacted = compact_delivery_entrypoints(output)
    if compacted:
        audit_result.setdefault("migrations", []).extend(compacted)
    if audit_result.get("migrations"):
        audit_result["migrations"] = list(dict.fromkeys(audit_result["migrations"]))

    (output / "FLAG_UPDATE.md").write_text(update_runbook(contract), encoding="utf-8")
    (output / "VERIFY.md").write_text(
        "# Verification\n\n"
        "Run `python3 scripts/ctfctl.py verify --project-dir <delivery>` after Docker is available.\n",
        encoding="utf-8",
    )
    manifest = manifest_for(output, audit_result)
    manifest["status"] = prepared_status
    (output / "delivery-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"status": prepared_status, "output": str(output), "contract": contract, "manifest": str(output / "delivery-manifest.json"), "audit": audit_result}


def docker_available() -> bool:
    return shutil.which("docker") is not None and run(["docker", "info"], timeout=20).returncode == 0


def probe_http(host: str, port: int, path: str, expected: int | None) -> Dict[str, Any]:
    url = f"http://{host}:{port}{path or '/'}"
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            status = int(response.status)
            ok = expected is None or status == expected
            return {"type": "http", "url": url, "status": status, "status_result": "passed" if ok else "failed"}
    except urllib.error.HTTPError as exc:
        ok = expected is None or exc.code == expected
        return {"type": "http", "url": url, "status": exc.code, "status_result": "passed" if ok else "failed"}
    except Exception as exc:
        return {"type": "http", "url": url, "status_result": "failed", "error": str(exc)}


def probe_tcp(host: str, port: int) -> Dict[str, Any]:
    try:
        with socket.create_connection((host, port), timeout=5):
            return {"type": "tcp", "host": host, "port": port, "status_result": "passed"}
    except Exception as exc:
        return {"type": "tcp", "host": host, "port": port, "status_result": "failed", "error": str(exc)}


def verify(project: Path, image: str, keep: bool = False) -> Dict[str, Any]:
    audit_result = audit(project)
    challenge, _ = read_challenge(project)
    if not docker_available():
        return {"status": "environment_failed", "verification": "runtime", "reason": "Docker daemon unavailable", "audit": audit_result}
    dockerfile = project / "Dockerfile"
    if not dockerfile.exists():
        return {"status": "failed", "verification": "build", "reason": "Dockerfile missing", "audit": audit_result}
    project_key = hashlib.sha1(str(project).encode("utf-8")).hexdigest()[:8]
    tag = image or f"ctfbuild-{re.sub(r'[^a-z0-9_.-]+', '-', project.name.lower()).strip('-') or 'challenge'}-{project_key}:verify"
    build = run(["docker", "build", "-t", tag, "."], cwd=project, timeout=900)
    result: Dict[str, Any] = {"status": "failed", "image": tag, "build": {"returncode": build.returncode, "stdout": build.stdout[-4000:], "stderr": build.stderr[-4000:]}, "audit": audit_result}
    if build.returncode != 0:
        result["verification"] = "build"
        return result
    name = f"ctfverify-{os.getpid()}-{int(time.time())}"
    ports = [int(value) for value in (audit_result["runtime"].get("ports") or []) if str(value).isdigit()]
    run_cmd = ["docker", "run", "-d", "--name", name]
    if ports:
        run_cmd += ["-p", f"127.0.0.1::{ports[0]}"]
    run_cmd += [tag, "/start.sh"]
    started = run(run_cmd, cwd=project, timeout=60)
    result["run"] = {"returncode": started.returncode, "stdout": started.stdout.strip(), "stderr": started.stderr[-3000:]}
    if started.returncode != 0:
        result["verification"] = "runtime"
        return result
    container = started.stdout.strip()
    try:
        time.sleep(2)
        inspect = run(["docker", "inspect", "-f", "{{.State.Running}}", container], timeout=20)
        result["running"] = inspect.stdout.strip() == "true"
        if not result["running"]:
            result["status"] = "failed"
            result["verification"] = "runtime"
            return result
        contract = audit_result["contract"]
        flag = contract["flag"]
        if flag["mode"] == "direct_exec":
            value = "flag{ctfctl_verify_runtime}"
            inject = run(["docker", "exec", container, "sh", "-c", 'printf "%s\\n" "$1" > "$2"', "sh", value, flag["path"]], timeout=20)
            readback = run(["docker", "exec", container, "sh", "-c", 'cat "$1"', "sh", flag["path"]], timeout=20)
            result["flag"] = {"mode": flag["mode"], "path": flag["path"], "write_returncode": inject.returncode, "readback": readback.stdout.strip(), "status_result": "passed" if inject.returncode == 0 and readback.stdout.strip() == value else "failed"}
        else:
            result["flag"] = {"mode": flag["mode"], "path": flag["path"], "status_result": "partial", "reason": "该 Flag 模式需要题目专用更新命令"}
        if ports:
            port_info = run(["docker", "port", container, str(ports[0])], timeout=20)
            match = re.search(r":(\d+)$", port_info.stdout.strip())
            if match:
                host_port = int(match.group(1))
                verification = challenge.get("verification") if isinstance(challenge.get("verification"), dict) else {}
                probe = verification.get("solve_probe") if isinstance(verification.get("solve_probe"), dict) else {}
                probe_type = str(probe.get("type") or "http").lower()
                if probe_type == "tcp":
                    result["probe"] = probe_tcp("127.0.0.1", host_port)
                else:
                    result["probe"] = probe_http("127.0.0.1", host_port, str(probe.get("path") or "/"), int(probe["expect_status"]) if str(probe.get("expect_status") or "").isdigit() else None)
        checks = [result.get("running", False), result.get("flag", {}).get("status_result") in {"passed", "partial"}]
        if result.get("probe"):
            checks.append(result["probe"].get("status_result") == "passed")
        result["status"] = "passed" if all(checks) else "partial"
        result["verification"] = "runtime+flag+probe"
    finally:
        if not keep:
            run(["docker", "rm", "-f", container], timeout=30)
    return result


def package(project: Path, output: Path) -> Dict[str, Any]:
    if not project.is_dir():
        raise RuntimeError(f"交付目录不存在: {project}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(output, "w:gz") as archive:
        archive.add(project, arcname=project.name, recursive=True, filter=lambda info: None if any(part in IGNORED_NAMES for part in Path(info.name).parts) else info)
    data = output.read_bytes()
    return {"status": "passed", "archive": str(output), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Evidence-first CTF delivery compiler")
    sub = p.add_subparsers(dest="command", required=True)
    for name in ("audit", "prepare", "verify"):
        item = sub.add_parser(name)
        item.add_argument("--project-dir", required=True)
        item.add_argument("--format", choices=("text", "json"), default="text")
    sub.choices["prepare"].add_argument("--output", default="")
    sub.choices["prepare"].add_argument("--force", action="store_true")
    sub.choices["verify"].add_argument("--image", default="")
    sub.choices["verify"].add_argument("--keep", action="store_true")
    item = sub.add_parser("package")
    item.add_argument("--project-dir", required=True)
    item.add_argument("--output", required=True)
    item.add_argument("--format", choices=("text", "json"), default="text")
    return p


def emit(payload: Dict[str, Any], fmt: str) -> int:
    if fmt == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"status: {payload.get('status')}")
        for key in ("output", "archive", "verification", "reason", "manifest"):
            if payload.get(key):
                print(f"{key}: {payload[key]}")
    return 0 if payload.get("status") in {"passed", "partial"} else 1


def main() -> int:
    args = parser().parse_args()
    try:
        project = Path(args.project_dir).resolve()
        if args.command == "audit":
            return emit(audit(project), args.format)
        if args.command == "prepare":
            output = Path(args.output).resolve() if args.output else project / "dist"
            return emit(prepare(project, output, args.force), args.format)
        if args.command == "verify":
            return emit(verify(project, args.image, args.keep), args.format)
        return emit(package(project, Path(args.output).resolve()), args.format)
    except (RuntimeError, ValueError, OSError) as exc:
        reason = str(exc)
        status = "environment_failed" if "PyYAML" in reason or "Docker daemon" in reason else "failed"
        return emit({"status": status, "reason": reason}, getattr(args, "format", "text"))


if __name__ == "__main__":
    raise SystemExit(main())
