#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List

from audit_input import audit_project, can_auto_proceed, proposal_gate_required
from derive_config import derive
from parse_config_block import _extract_proposal, _load_yaml_module, build_challenge, write_yaml
from result_utils import dump_json, read_json, sha256_file, structured_error, structured_ok, write_json
from utils import ConfigError, write_unix_text


SCHEMA_VERSION = "1.0"
SCRIPT_DIR = Path(__file__).resolve().parent
VALIDATE_SH = SCRIPT_DIR / "validate.sh"
RENDER_PY = SCRIPT_DIR / "render.py"


def state_dir(project_dir: Path) -> Path:
    return project_dir / ".ctfbuild"


def session_path(project_dir: Path) -> Path:
    return state_dir(project_dir) / "session.json"


def proposal_json_path(project_dir: Path) -> Path:
    return state_dir(project_dir) / "proposal.json"


def proposal_yaml_path(project_dir: Path) -> Path:
    return state_dir(project_dir) / "proposal.yaml"


def accepted_path(project_dir: Path) -> Path:
    return state_dir(project_dir) / "accepted_proposal.json"


def default_render_dir(project_dir: Path) -> Path:
    return state_dir(project_dir) / "rendered"


def default_challenge_path(project_dir: Path) -> Path:
    return project_dir / "challenge.yaml"


def windows_drive_to_wsl_path(value: str) -> str:
    text = str(value).replace("\\", "/")
    if text.startswith("/mnt/"):
        return text
    match = re.match(r"^([A-Za-z]):/?(.*)$", text)
    if not match:
        return text
    drive = match.group(1).lower()
    rest = match.group(2).lstrip("/")
    return f"/mnt/{drive}/{rest}" if rest else f"/mnt/{drive}"


def is_wsl_bash(bash_path: str) -> bool:
    text = str(bash_path or "").replace("\\", "/").lower()
    return text.endswith("/windows/system32/bash.exe") or text.endswith("/windows/sysnative/bash.exe")


def build_validate_command(
    *,
    project_dir: Path,
    validate_sh: Path,
    dockerfile: Path,
    start_sh: Path,
    challenge_path: Path,
    json_summary: Path,
    with_dynamic_flag: bool = False,
    platform_name: str | None = None,
    bash_executable: str | None = None,
) -> tuple[List[str], str | None]:
    platform_name = platform_name or os.name
    bash_executable = bash_executable or shutil.which("bash") or "bash"
    args = [
        str(validate_sh),
        "--json-summary",
        str(json_summary),
        str(dockerfile),
        str(start_sh),
        str(challenge_path),
    ]
    if with_dynamic_flag:
        args.insert(1, "--with-dynamic-flag")
    if platform_name == "nt" and is_wsl_bash(bash_executable):
        wsl_args = [windows_drive_to_wsl_path(item) if looks_like_windows_path(item) else item for item in args]
        shell = "cd " + shlex.quote(windows_drive_to_wsl_path(str(project_dir))) + " && bash " + " ".join(
            shlex.quote(item) for item in wsl_args
        )
        return [bash_executable, "-lc", shell], None
    return [bash_executable, *args], str(project_dir)


def looks_like_windows_path(value: str) -> bool:
    return bool(re.match(r"^[A-Za-z]:[\\/]", str(value)))


def run_validate_command(
    *,
    project_dir: Path,
    dockerfile: Path,
    start_sh: Path,
    challenge_path: Path,
    json_summary: Path,
    with_dynamic_flag: bool = False,
    capture_output: bool = False,
) -> subprocess.CompletedProcess[str]:
    cmd, cwd = build_validate_command(
        project_dir=project_dir,
        validate_sh=VALIDATE_SH,
        dockerfile=dockerfile,
        start_sh=start_sh,
        challenge_path=challenge_path,
        json_summary=json_summary,
        with_dynamic_flag=with_dynamic_flag,
    )
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=capture_output)


def write_session(
    project_dir: Path,
    *,
    stage: str,
    audit: Dict[str, Any],
    challenge_path: Path,
    last_result: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    session = {
        "schema_version": SCHEMA_VERSION,
        "project_dir": str(project_dir),
        "stage": stage,
        "risk_level": audit.get("risk_level", "clean"),
        "recommended_path": audit.get("recommended_path", "direct_render"),
        "support_level": audit.get("support_level", "supported"),
        "verification_level": audit.get("verification_level", "static"),
        "manual_required": bool(audit.get("manual_required")),
        "gates": audit.get("gates", {}),
        "proposal_path": str(proposal_yaml_path(project_dir)),
        "accepted_proposal_path": str(accepted_path(project_dir)),
        "challenge_path": str(challenge_path),
        "last_result": last_result or {},
    }
    write_json(session_path(project_dir), session)
    return session


def load_session(project_dir: Path) -> Dict[str, Any]:
    path = session_path(project_dir)
    if not path.exists():
        return {}
    return read_json(path)


def emit(payload: Dict[str, Any], fmt: str) -> None:
    if fmt == "json":
        print(dump_json(payload, pretty=True))
        return
    if payload.get("ok") is False:
        print(f"[ERROR] {payload.get('code')}: {payload.get('summary')}", file=sys.stderr)
        hint = payload.get("hint")
        if hint:
            print(f"[HINT] {hint}", file=sys.stderr)
        return
    print(f"[OK] {payload.get('summary', payload.get('stage', 'done'))}")


def load_yaml_object(path: Path) -> Dict[str, Any]:
    yaml_mod = _load_yaml_module()
    loaded = yaml_mod.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ConfigError(f"YAML 顶层必须是对象: {path}")
    return loaded


def command_intake(args: argparse.Namespace) -> int:
    project_dir = Path(args.project_dir).resolve()
    challenge_path = Path(args.config).resolve() if args.config else default_challenge_path(project_dir)
    audit = audit_project(project_dir, challenge_path=challenge_path if challenge_path.exists() else None)
    write_session(project_dir, stage="intake", audit=audit, challenge_path=challenge_path)
    emit(structured_ok("intake", summary="input audit completed", input_audit=audit), args.format)
    return 0


def command_propose(args: argparse.Namespace) -> int:
    project_dir = Path(args.project_dir).resolve()
    proposal = derive(project_dir)
    state_dir(project_dir).mkdir(parents=True, exist_ok=True)
    write_json(proposal_json_path(project_dir), proposal)
    yaml_mod = _load_yaml_module()
    write_unix_text(proposal_yaml_path(project_dir), yaml_mod.safe_dump(proposal, sort_keys=False, allow_unicode=True))
    challenge_path = default_challenge_path(project_dir)
    audit = audit_project(project_dir, challenge_path=challenge_path) if challenge_path.exists() else proposal["input_audit"]
    write_session(project_dir, stage="proposal_ready", audit=audit, challenge_path=default_challenge_path(project_dir))
    emit(
        structured_ok(
            "propose",
            summary="proposal generated",
            proposal_path=str(proposal_yaml_path(project_dir)),
            input_audit=audit,
        ),
        args.format,
    )
    return 0


def command_accept(args: argparse.Namespace) -> int:
    project_dir = Path(args.project_dir).resolve()
    proposal_path = Path(args.proposal).resolve() if args.proposal else proposal_yaml_path(project_dir)
    challenge_path = Path(args.output).resolve() if args.output else default_challenge_path(project_dir)
    challenge_existed = challenge_path.exists()
    if args.refresh:
        if not challenge_path.exists():
            raise ConfigError(f"--refresh 需要已存在的 challenge.yaml: {challenge_path}")
        if args.format == "text":
            print(f"[INFO] file plan: {challenge_path} -> keep")
    else:
        proposal_root = load_yaml_object(proposal_path)
        proposal = _extract_proposal(proposal_root)
        challenge_doc = build_challenge(proposal, SimpleNamespace(name=args.name or "", output=str(challenge_path)))
        write_yaml(challenge_doc, challenge_path)

    proposal_hash = sha256_file(proposal_path) if proposal_path.exists() else ""
    accepted = {
        "schema_version": SCHEMA_VERSION,
        "accepted": True,
        "proposal_sha256": proposal_hash,
        "challenge_sha256": sha256_file(challenge_path),
        "source": str(proposal_path) if proposal_hash else "current-challenge",
        "manual_notes": args.notes or "",
        "refresh": bool(args.refresh),
    }
    write_json(accepted_path(project_dir), accepted)
    audit = audit_project(project_dir, challenge_path=challenge_path)
    write_session(project_dir, stage="proposal_accepted", audit=audit, challenge_path=challenge_path)
    if args.format == "text" and not args.refresh:
        action = "overwrite" if challenge_existed else "create"
        print(f"[INFO] file plan: {challenge_path} -> {action}")
    emit(
        structured_ok(
            "accept",
            summary="proposal accepted",
            challenge_path=str(challenge_path),
            accepted_proposal_path=str(accepted_path(project_dir)),
            input_audit=audit,
            file_plan=[
                {
                    "path": str(challenge_path),
                    "action": "keep" if args.refresh else ("overwrite" if challenge_existed else "create"),
                    "exists_before": challenge_existed,
                }
            ],
        ),
        args.format,
    )
    return 0


def _accepted_matches(project_dir: Path, challenge_path: Path) -> bool:
    path = accepted_path(project_dir)
    if not path.exists() or not challenge_path.exists():
        return False
    data = read_json(path)
    if not data.get("accepted"):
        return False
    return data.get("challenge_sha256") == sha256_file(challenge_path)


def command_render(args: argparse.Namespace) -> int:
    project_dir = Path(args.project_dir).resolve()
    challenge_path = Path(args.config).resolve() if args.config else default_challenge_path(project_dir)
    output_dir = Path(args.output).resolve() if args.output else default_render_dir(project_dir)
    audit = audit_project(project_dir, challenge_path=challenge_path if challenge_path.exists() else None)
    gate_required = proposal_gate_required(audit)
    if gate_required and not args.manual and not _accepted_matches(project_dir, challenge_path):
        payload = structured_error(
            "render",
            "CONFIG_PROPOSAL_NOT_ACCEPTED",
            "当前输入需要先接受 proposal，render 已拒绝。",
            file=str(challenge_path),
            hint="执行 workflow.py propose，再执行 workflow.py accept；如为人工确认场景，使用 --manual --reason。",
            support_level=audit.get("support_level", "partial"),
        )
        write_session(project_dir, stage="render_blocked", audit=audit, challenge_path=challenge_path, last_result=payload)
        emit(payload, args.format)
        return 2
    if args.manual and not args.reason.strip():
        payload = structured_error(
            "render",
            "RENDER_MANUAL_REASON_REQUIRED",
            "--manual 必须同时提供 --reason。",
            hint="示例：--manual --reason \"trusted regression example\"",
            support_level=audit.get("support_level", "partial"),
        )
        emit(payload, args.format)
        return 2

    cmd: List[str] = [
        sys.executable,
        str(RENDER_PY),
        "--config",
        str(challenge_path),
        "--output",
        str(output_dir),
        "--format",
        args.format,
    ]
    if args.manual:
        cmd.extend(["--manual", "--reason", args.reason])
    result = subprocess.run(cmd, cwd=str(project_dir), text=True, capture_output=True)
    if result.stdout:
        sys.stdout.write(result.stdout)
    if result.stderr:
        sys.stderr.write(result.stderr)
    stage = "rendered" if result.returncode == 0 else "render_failed"
    last_result = {"ok": result.returncode == 0, "returncode": result.returncode, "output_dir": str(output_dir)}
    write_session(project_dir, stage=stage, audit=audit, challenge_path=challenge_path, last_result=last_result)
    return result.returncode


def command_reviewed_render(args: argparse.Namespace) -> int:
    project_dir = Path(args.project_dir).resolve()
    challenge_path = Path(args.config).resolve() if args.config else default_challenge_path(project_dir)
    output_dir = Path(args.output).resolve() if args.output else default_render_dir(project_dir)
    if not challenge_path.exists():
        payload = structured_error(
            "reviewed-render",
            "CONFIG_CHALLENGE_NOT_FOUND",
            "reviewed-render 需要已存在的 challenge.yaml。",
            file=str(challenge_path),
            hint="先执行 workflow.py propose/accept，或提供 --config。",
        )
        emit(payload, args.format)
        return 2
    if not args.reason.strip():
        payload = structured_error(
            "reviewed-render",
            "RENDER_REVIEW_REASON_REQUIRED",
            "reviewed-render 必须提供 --reason。",
            hint="示例：--reason \"reviewed explicit low-risk challenge.yaml\"",
        )
        emit(payload, args.format)
        return 2

    audit = audit_project(project_dir, challenge_path=challenge_path)
    accepted = _accepted_matches(project_dir, challenge_path)
    if proposal_gate_required(audit) and not accepted:
        payload = structured_error(
            "reviewed-render",
            "CONFIG_REVIEWED_RENDER_BLOCKED",
            "当前输入仍需要 proposal/accept，reviewed-render 已拒绝。",
            file=str(challenge_path),
            hint="执行 workflow.py propose 与 workflow.py accept；确认后可重新运行 reviewed-render。",
            support_level=audit.get("support_level", "partial"),
        )
        write_session(project_dir, stage="reviewed_render_blocked", audit=audit, challenge_path=challenge_path, last_result=payload)
        emit(payload, args.format)
        return 2

    cmd: List[str] = [
        sys.executable,
        str(RENDER_PY),
        "--config",
        str(challenge_path),
        "--output",
        str(output_dir),
        "--format",
        args.format,
        "--manual",
        "--reason",
        f"reviewed-render: {args.reason.strip()}",
    ]
    result = subprocess.run(cmd, cwd=str(project_dir), text=True, capture_output=True)
    if result.stdout:
        sys.stdout.write(result.stdout)
    if result.stderr:
        sys.stderr.write(result.stderr)
    stage = "rendered" if result.returncode == 0 else "render_failed"
    last_result = {
        "ok": result.returncode == 0,
        "returncode": result.returncode,
        "output_dir": str(output_dir),
        "reviewed_render": True,
        "reason": args.reason.strip(),
        "accepted_proposal": accepted,
    }
    write_session(project_dir, stage=stage, audit=audit, challenge_path=challenge_path, last_result=last_result)
    return result.returncode


def _derive_challenge_yaml(project_dir: Path, challenge_path: Path, *, name: str = "") -> Dict[str, Any]:
    proposal = derive(project_dir)
    state_dir(project_dir).mkdir(parents=True, exist_ok=True)
    write_json(proposal_json_path(project_dir), proposal)
    yaml_mod = _load_yaml_module()
    write_unix_text(proposal_yaml_path(project_dir), yaml_mod.safe_dump(proposal, sort_keys=False, allow_unicode=True))
    config_proposal = _extract_proposal(proposal)
    challenge_doc = build_challenge(config_proposal, SimpleNamespace(name=name, output=str(challenge_path)))
    write_yaml(challenge_doc, challenge_path)
    return proposal


def command_auto_render(args: argparse.Namespace) -> int:
    project_dir = Path(args.project_dir).resolve()
    challenge_path = Path(args.config).resolve() if args.config else default_challenge_path(project_dir)
    output_dir = Path(args.output).resolve() if args.output else default_render_dir(project_dir)
    json_summary = Path(args.json_summary).resolve() if args.json_summary else state_dir(project_dir) / "validate-summary.json"
    state_dir(project_dir).mkdir(parents=True, exist_ok=True)

    initial_audit = audit_project(project_dir, challenge_path=challenge_path if challenge_path.exists() else None)
    can_auto, blockers = can_auto_proceed(initial_audit)
    if not can_auto:
        payload = structured_error(
            "auto-render",
            "AUTO_RENDER_BLOCKED",
            "当前题目目录不适合自动生成平台交付件。",
            file=str(project_dir),
            hint="先人工处理阻塞项，再重新运行 auto-render。",
        )
        payload.update({"blockers": blockers, "input_audit": initial_audit})
        write_session(project_dir, stage="auto_render_blocked", audit=initial_audit, challenge_path=challenge_path, last_result=payload)
        emit(payload, args.format)
        return 2

    derived_proposal: Dict[str, Any] = {}
    derived_challenge = False
    if not challenge_path.exists():
        try:
            derived_proposal = _derive_challenge_yaml(project_dir, challenge_path, name=args.name or "")
            derived_challenge = True
        except ConfigError as exc:
            payload = structured_error(
                "auto-render",
                "AUTO_RENDER_DERIVE_FAILED",
                str(exc),
                file=str(challenge_path),
                hint="检查目录是否包含可推断的源码、端口和启动方式。",
            )
            payload.update({"input_audit": initial_audit})
            write_session(project_dir, stage="auto_render_failed", audit=initial_audit, challenge_path=challenge_path, last_result=payload)
            emit(payload, args.format)
            return 2

    audit = audit_project(project_dir, challenge_path=challenge_path)
    can_auto, blockers = can_auto_proceed(audit)
    if not can_auto:
        payload = structured_error(
            "auto-render",
            "AUTO_RENDER_BLOCKED_AFTER_DERIVE",
            "推导 challenge.yaml 后仍不适合自动生成平台交付件。",
            file=str(challenge_path),
            hint="保留已生成的 challenge.yaml，人工修订后重新运行 auto-render。",
        )
        payload.update({"blockers": blockers, "input_audit": audit})
        write_session(project_dir, stage="auto_render_blocked", audit=audit, challenge_path=challenge_path, last_result=payload)
        emit(payload, args.format)
        return 2

    render_cmd: List[str] = [
        sys.executable,
        str(RENDER_PY),
        "--config",
        str(challenge_path),
        "--output",
        str(output_dir),
        "--format",
        args.format,
        "--manual",
        "--reason",
        "auto-render: Dockerizer handoff generated by CloverSec workflow",
    ]
    render_result = subprocess.run(render_cmd, cwd=str(project_dir), text=True, capture_output=True)
    if render_result.stdout:
        sys.stdout.write(render_result.stdout)
    if render_result.stderr:
        sys.stderr.write(render_result.stderr)
    if render_result.returncode != 0:
        payload = structured_error(
            "auto-render",
            "AUTO_RENDER_RENDER_FAILED",
            "平台交付文件生成失败。",
            file=str(challenge_path),
        )
        payload.update({"returncode": render_result.returncode, "stdout": render_result.stdout, "stderr": render_result.stderr})
        write_session(project_dir, stage="auto_render_failed", audit=audit, challenge_path=challenge_path, last_result=payload)
        emit(payload, args.format)
        return render_result.returncode

    validate_result = run_validate_command(
        project_dir=project_dir,
        dockerfile=output_dir / "Dockerfile",
        start_sh=output_dir / "start.sh",
        challenge_path=challenge_path,
        json_summary=json_summary,
        with_dynamic_flag=True,
        capture_output=True,
    )
    if validate_result.stdout:
        sys.stdout.write(validate_result.stdout)
    if validate_result.stderr:
        sys.stderr.write(validate_result.stderr)

    stage = "auto_render_validated" if validate_result.returncode == 0 else "auto_render_failed"
    last_result = {
        "ok": validate_result.returncode == 0,
        "returncode": validate_result.returncode,
        "challenge_path": str(challenge_path),
        "output_dir": str(output_dir),
        "validate_summary": str(json_summary),
        "derived_challenge": derived_challenge,
        "assumptions": [
            "auto-render 只完成平台交付文件生成和契约校验",
            "真实 Docker build/run/export 仍需后续授权执行",
        ],
        "unconfirmed": [
            "题目是否可解",
            "动态 flag 是否被业务逻辑正确读取",
            "运行时服务是否符合原题预期",
        ],
        "blockers": [] if validate_result.returncode == 0 else ["validate.sh 契约校验未通过"],
    }
    if derived_proposal:
        last_result["proposal_path"] = str(proposal_yaml_path(project_dir))
    write_session(project_dir, stage=stage, audit=audit, challenge_path=challenge_path, last_result=last_result)
    if validate_result.returncode != 0:
        payload = structured_error(
            "auto-render",
            "AUTO_RENDER_VALIDATE_FAILED",
            "平台交付文件已生成，但契约校验未通过。",
            file=str(json_summary),
        )
        payload.update(
            {
                "returncode": validate_result.returncode,
                "output_dir": str(output_dir),
                "validate_summary": str(json_summary),
            }
        )
        emit(payload, args.format)
        return validate_result.returncode
    emit(
        structured_ok(
            "auto-render",
            summary="auto-render completed and contract validation passed",
            challenge_path=str(challenge_path),
            output_dir=str(output_dir),
            validate_summary=str(json_summary),
            derived_challenge=derived_challenge,
            assumptions=last_result["assumptions"],
            unconfirmed=last_result["unconfirmed"],
        ),
        args.format,
    )
    return 0


def command_validate(args: argparse.Namespace) -> int:
    project_dir = Path(args.project_dir).resolve()
    challenge_path = Path(args.config).resolve() if args.config else default_challenge_path(project_dir)
    output_dir = Path(args.output).resolve() if args.output else default_render_dir(project_dir)
    dockerfile = output_dir / "Dockerfile"
    start_sh = output_dir / "start.sh"
    json_summary = Path(args.json_summary).resolve() if args.json_summary else state_dir(project_dir) / "validate-summary.json"
    result = run_validate_command(
        project_dir=project_dir,
        dockerfile=dockerfile,
        start_sh=start_sh,
        challenge_path=challenge_path,
        json_summary=json_summary,
    )
    audit = audit_project(project_dir, challenge_path=challenge_path if challenge_path.exists() else None)
    write_session(
        project_dir,
        stage="validated" if result.returncode == 0 else "validate_failed",
        audit=audit,
        challenge_path=challenge_path,
        last_result={"ok": result.returncode == 0, "returncode": result.returncode, "json_summary": str(json_summary)},
    )
    return result.returncode


def command_status(args: argparse.Namespace) -> int:
    project_dir = Path(args.project_dir).resolve()
    session = load_session(project_dir)
    if not session:
        payload = structured_error(
            "status",
            "INTAKE_SESSION_NOT_FOUND",
            "未找到 .ctfbuild/session.json。",
            hint="先执行 workflow.py intake 或 workflow.py propose。",
        )
        emit(payload, args.format)
        return 2
    if args.format == "json":
        print(dump_json(session, pretty=True))
    else:
        print(f"stage: {session.get('stage')}")
        print(f"risk_level: {session.get('risk_level')}")
        print(f"recommended_path: {session.get('recommended_path')}")
        print(f"support_level: {session.get('support_level')}")
        print(f"verification_level: {session.get('verification_level')}")
        print(f"manual_required: {str(session.get('manual_required')).lower()}")
        print(f"proposal_path: {session.get('proposal_path')}")
        print(f"accepted_proposal_path: {session.get('accepted_proposal_path')}")
        print(f"challenge_path: {session.get('challenge_path')}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CloverSec CTF Dockerizer workflow entrypoint.")
    parser.add_argument("--pretty", action="store_true", help="兼容旧习惯；等价于 --format json")
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--project-dir", default=".", help="题目目录")
        p.add_argument("--format", choices=("text", "json"), default="text")
        p.add_argument(
            "--pretty",
            action="store_true",
            default=argparse.SUPPRESS,
            help="兼容旧习惯；等价于 --format json",
        )

    p = sub.add_parser("intake", help="审计输入并写入 session")
    common(p)
    p.add_argument("--config", help="challenge.yaml 路径")
    p.set_defaults(func=command_intake)

    p = sub.add_parser("propose", help="生成 proposal.json/proposal.yaml")
    common(p)
    p.set_defaults(func=command_propose)

    p = sub.add_parser("accept", help="接受 proposal 并生成 challenge.yaml")
    common(p)
    p.add_argument("--proposal", help="proposal.yaml 路径")
    p.add_argument("--output", help="challenge.yaml 输出路径")
    p.add_argument("--name", default="", help="challenge.name 覆盖值")
    p.add_argument("--notes", default="", help="人工备注")
    p.add_argument("--refresh", action="store_true", help="登记当前 challenge.yaml 为已确认，不重新生成")
    p.set_defaults(func=command_accept)

    p = sub.add_parser("render", help="执行 gate 检查后渲染")
    common(p)
    p.add_argument("--config", help="challenge.yaml 路径")
    p.add_argument("--output", help="渲染目录，默认 .ctfbuild/rendered")
    p.add_argument("--manual", action="store_true", help="人工确认后绕过 gate")
    p.add_argument("--reason", default="", help="manual 原因")
    p.set_defaults(func=command_render)

    p = sub.add_parser("reviewed-render", help="低风险或已接受 proposal 的快速渲染入口")
    common(p)
    p.add_argument("--config", help="challenge.yaml 路径")
    p.add_argument("--output", help="渲染目录，默认 .ctfbuild/rendered")
    p.add_argument("--reason", default="", help="人工审查原因，必填")
    p.set_defaults(func=command_reviewed_render)

    p = sub.add_parser("auto-render", help="自动推导 challenge.yaml、渲染平台交付件并执行契约校验")
    common(p)
    p.add_argument("--config", help="challenge.yaml 路径")
    p.add_argument("--output", help="渲染目录，默认 .ctfbuild/rendered")
    p.add_argument("--json-summary", help="validate JSON 摘要路径")
    p.add_argument("--name", default="", help="challenge.name 覆盖值")
    p.set_defaults(func=command_auto_render)

    p = sub.add_parser("validate", help="校验渲染产物")
    common(p)
    p.add_argument("--config", help="challenge.yaml 路径")
    p.add_argument("--output", help="渲染目录，默认 .ctfbuild/rendered")
    p.add_argument("--json-summary", help="validate JSON 摘要路径")
    p.set_defaults(func=command_validate)

    p = sub.add_parser("status", help="查看 session 状态")
    common(p)
    p.set_defaults(func=command_status)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if getattr(args, "pretty", False):
        args.format = "json"
    try:
        return int(args.func(args))
    except ConfigError as exc:
        payload = structured_error("workflow", "CONFIG_WORKFLOW_FAILED", str(exc))
        emit(payload, getattr(args, "format", "text"))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
