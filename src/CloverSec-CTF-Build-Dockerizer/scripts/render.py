#!/usr/bin/env python3
"""将 challenge.yaml 或 CLI 参数渲染为 Dockerfile/start.sh/flag。"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
DATA_DIR = SKILL_ROOT / "data"
TEMPLATES_DIR = SKILL_ROOT / "templates"

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from utils import (  # noqa: E402
    ConfigError,
    build_copy_app,
    build_docker_env_lines,
    build_env_exports,
    build_npm_install_block,
    build_pip_requirements_block,
    build_runtime_deps_install,
    detect_stack,
    ensure_dict,
    ensure_list,
    first_non_empty,
    infer_from_patterns,
    load_patterns,
    load_stack_defs,
    load_template_with_includes,
    load_yaml_file,
    normalize_ports,
    render_template,
    validate_rendered,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="渲染 CTF Web Dockerfile/start.sh")
    parser.add_argument("--config", help="challenge.yaml 路径")

    parser.add_argument("--stack", help="技术栈: node/php/python/java/tomcat/lamp/pwn/ai/rdg")
    parser.add_argument("--port", action="append", help="暴露端口，可重复传入")
    parser.add_argument("--workdir", help="WORKDIR，默认取栈默认值")
    parser.add_argument("--start", dest="start_cmd", help="启动命令")
    parser.add_argument("--base-image", help="覆盖基础镜像")
    parser.add_argument("--app-src", help="应用源码路径，默认 .")
    parser.add_argument("--app-dst", help="容器内应用路径，默认等于 WORKDIR")
    parser.add_argument("--mode", choices=["cmd", "service", "supervisor"], help="start.mode")
    parser.add_argument("--runtime-dep", action="append", default=[], help="额外运行依赖，可重复")
    parser.add_argument("--env", action="append", default=[], help="环境变量 KEY=VALUE，可重复")

    parser.add_argument("--output", default=".", help="输出目录，默认当前目录")
    parser.add_argument("--detect-debug", action="store_true", help="打印栈侦测详情")
    return parser.parse_args()


def parse_cli_env(env_items: List[str]) -> Dict[str, str]:
    env_map: Dict[str, str] = {}
    for item in env_items:
        if "=" not in item:
            raise ConfigError(f"--env 参数格式错误（需要 KEY=VALUE）: {item}")
        key, value = item.split("=", 1)
        key = key.strip()
        if not key:
            raise ConfigError(f"--env 参数格式错误（缺少 KEY）: {item}")
        env_map[key] = value
    return env_map


def choose_stack(
    cli_stack: str,
    cfg_stack: str,
    stacks: Dict[str, Dict[str, Any]],
    scan_dir: Path,
) -> Tuple[str, bool, float, List[Dict[str, Any]]]:
    if cli_stack:
        if cli_stack not in stacks:
            raise ConfigError(f"不支持的 stack: {cli_stack}")
        _, _, details = detect_stack(scan_dir, stacks)
        return cli_stack, False, 0.0, details

    if cfg_stack:
        if cfg_stack not in stacks:
            raise ConfigError(f"配置中的 stack 不支持: {cfg_stack}")
        _, _, details = detect_stack(scan_dir, stacks)
        return cfg_stack, False, 0.0, details

    detected_id, confidence, details = detect_stack(scan_dir, stacks)
    if not detected_id:
        raise ConfigError(
            "未能自动侦测技术栈。请使用 --stack 指定，或在当前目录放置可识别特征文件。"
        )
    return detected_id, True, confidence, details


def load_challenge_config(config_path: Path) -> Dict[str, Any]:
    raw = load_yaml_file(config_path)
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ConfigError("challenge.yaml 顶层必须是对象")

    challenge = raw.get("challenge")
    if challenge is None:
        raise ConfigError("challenge.yaml 缺少 challenge 顶层字段")
    return ensure_dict(challenge, "challenge")


def resolve_scan_dir(config_arg: str | None) -> Path:
    """优先在 challenge.yaml 所在目录扫描特征，避免跨目录执行时误判。"""
    if config_arg:
        cfg_path = Path(config_arg).resolve()
        if not cfg_path.exists():
            raise ConfigError(f"challenge.yaml 不存在: {cfg_path}")
        return cfg_path.parent
    return Path.cwd()


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return bool(value)
    return True


def _to_bool(value: Any, field_name: str, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        v = value.strip().lower()
        if v in {"true", "1", "yes", "y"}:
            return True
        if v in {"false", "0", "no", "n"}:
            return False
    raise ConfigError(f"{field_name} 必须是布尔值")


def build_render_context(
    args: argparse.Namespace,
    stacks: Dict[str, Dict[str, Any]],
    patterns_data: Dict[str, Any],
) -> Dict[str, Any]:
    scan_dir = resolve_scan_dir(args.config)

    challenge: Dict[str, Any] = {}
    if args.config:
        challenge = load_challenge_config(Path(args.config))

    cfg_stack_raw = challenge.get("stack")
    cfg_stack = cfg_stack_raw.strip() if isinstance(cfg_stack_raw, str) else ""

    stack_id, auto_detected, confidence, detect_details = choose_stack(
        cli_stack=(args.stack or "").strip(),
        cfg_stack=cfg_stack,
        stacks=stacks,
        scan_dir=scan_dir,
    )

    stack_info = stacks[stack_id]
    defaults = ensure_dict(stack_info.get("defaults"), f"stacks[{stack_id}].defaults")

    start_cfg = ensure_dict(challenge.get("start"), "challenge.start")
    extra_cfg = ensure_dict(challenge.get("extra"), "challenge.extra")
    rdg_cfg = ensure_dict(challenge.get("rdg"), "challenge.rdg")

    mode = first_non_empty(args.mode, start_cfg.get("mode"), "cmd")
    if mode not in {"cmd", "service", "supervisor"}:
        raise ConfigError(f"不支持的 start.mode: {mode}")

    infer_info = infer_from_patterns(scan_dir, stack_id, patterns_data)

    inferred_base_image_raw = infer_info.get("base_image")
    inferred_base_image = (
        inferred_base_image_raw.strip() if isinstance(inferred_base_image_raw, str) else ""
    )

    base_image = first_non_empty(
        args.base_image,
        challenge.get("base_image"),
        inferred_base_image,
        defaults.get("base_image"),
    )
    workdir = first_non_empty(args.workdir, challenge.get("workdir"), defaults.get("workdir"), "/app")
    app_src = first_non_empty(args.app_src, challenge.get("app_src"), ".")
    app_dst = first_non_empty(args.app_dst, challenge.get("app_dst"), workdir)

    if not base_image:
        raise ConfigError("未找到可用基础镜像（base_image）")
    if not workdir:
        raise ConfigError("workdir 不能为空")

    # 端口优先级：CLI > challenge > patterns 推断 > stacks defaults
    ports_from_cli = normalize_ports(args.port) if args.port else []
    raw_cfg_ports = challenge.get("expose_ports")
    ports_from_cfg = normalize_ports(raw_cfg_ports) if _has_value(raw_cfg_ports) else []

    ports_source = "explicit"
    ports_reason = ""
    inference_notes: List[Dict[str, str]] = []

    if ports_from_cli:
        expose_ports = ports_from_cli
    elif ports_from_cfg:
        expose_ports = ports_from_cfg
    else:
        inferred_ports = normalize_ports(infer_info.get("ports"))
        if inferred_ports:
            expose_ports = inferred_ports
            ports_source = str(infer_info.get("ports_source", "rule"))
            ports_reason = str(infer_info.get("ports_reason", ""))
        else:
            expose_ports = normalize_ports(defaults.get("expose_ports"))
            ports_source = "default"
            ports_reason = "patterns 未给出端口，回退 stacks 默认值"

    if not expose_ports:
        raise ConfigError("expose_ports 不能为空，至少需要一个端口")

    # 启动命令优先级：CLI > challenge > patterns 推断 > stacks defaults
    cmd_from_cli = args.start_cmd.strip() if isinstance(args.start_cmd, str) and args.start_cmd.strip() else ""
    raw_cfg_cmd = start_cfg.get("cmd")
    cmd_from_cfg = raw_cfg_cmd.strip() if isinstance(raw_cfg_cmd, str) and raw_cfg_cmd.strip() else ""

    start_source = "explicit"
    start_reason = ""

    if cmd_from_cli:
        start_cmd = cmd_from_cli
    elif cmd_from_cfg:
        start_cmd = cmd_from_cfg
    else:
        inferred_raw = infer_info.get("start_cmd")
        inferred_start = inferred_raw.strip() if isinstance(inferred_raw, str) else ""
        if inferred_start:
            start_cmd = inferred_start
            start_source = str(infer_info.get("start_source", "rule"))
            start_reason = str(infer_info.get("start_reason", ""))
        else:
            fallback_raw = defaults.get("start_cmd")
            fallback = fallback_raw.strip() if isinstance(fallback_raw, str) else ""
            if not fallback:
                raise ConfigError("未找到可用启动命令，请通过 start.cmd 或 --start 提供")
            start_cmd = fallback
            start_source = "default"
            start_reason = "patterns 未命中，回退 stacks 默认启动命令"

    if mode == "cmd" and not start_cmd:
        raise ConfigError("mode=cmd 时必须提供启动命令（start.cmd 或 --start）")

    if not args.base_image and not _has_value(challenge.get("base_image")):
        if inferred_base_image:
            inference_notes.append(
                {
                    "field": "base_image",
                    "value": inferred_base_image,
                    "source": str(infer_info.get("base_image_source", "rule")),
                    "reason": str(infer_info.get("base_image_reason", "")),
                    "override": "--base-image 或 challenge.base_image",
                }
            )
        elif defaults.get("base_image"):
            inference_notes.append(
                {
                    "field": "base_image",
                    "value": str(defaults.get("base_image")),
                    "source": "default",
                    "reason": "patterns 未命中，回退 stacks 默认基础镜像",
                    "override": "--base-image 或 challenge.base_image",
                }
            )

    if ports_source != "explicit":
        inference_notes.append(
            {
                "field": "expose_ports",
                "value": " ".join(expose_ports),
                "source": ports_source,
                "reason": ports_reason,
                "override": "--port 或 challenge.expose_ports",
            }
        )

    if start_source != "explicit":
        inference_notes.append(
            {
                "field": "start_cmd",
                "value": start_cmd,
                "source": start_source,
                "reason": start_reason,
                "override": "--start 或 challenge.start.cmd",
            }
        )

    if args.runtime_dep:
        runtime_deps = args.runtime_dep
    else:
        runtime_deps = ensure_list(challenge.get("runtime_deps"), "challenge.runtime_deps")

    cli_env = parse_cli_env(args.env)
    env_map = cli_env if cli_env else ensure_dict(extra_cfg.get("env"), "challenge.extra.env")
    copy_items = ensure_list(extra_cfg.get("copy"), "challenge.extra.copy")
    npm_install_block = str(first_non_empty(extra_cfg.get("npm_install_block"), "") or "")
    pip_requirements_block = str(first_non_empty(extra_cfg.get("pip_requirements_block"), "") or "")

    rdg_enable_ttyd = _to_bool(rdg_cfg.get("enable_ttyd"), "challenge.rdg.enable_ttyd", True)
    rdg_ttyd_port_raw = first_non_empty(rdg_cfg.get("ttyd_port"), "8022")
    rdg_ttyd_port = str(rdg_ttyd_port_raw).strip()
    if not rdg_ttyd_port.isdigit() or not (1 <= int(rdg_ttyd_port) <= 65535):
        raise ConfigError("challenge.rdg.ttyd_port 必须是 1-65535 的端口数字")
    rdg_ttyd_login_cmd = str(first_non_empty(rdg_cfg.get("ttyd_login_cmd"), "/bin/bash")).strip()
    if not rdg_ttyd_login_cmd:
        raise ConfigError("challenge.rdg.ttyd_login_cmd 不能为空")

    return {
        "stack_id": stack_id,
        "stack_display": stack_info.get("display_name", stack_id),
        "auto_detected": auto_detected,
        "confidence": confidence,
        "detect_details": detect_details,
        "mode": mode,
        "base_image": str(base_image),
        "workdir": str(workdir),
        "app_src": str(app_src),
        "app_dst": str(app_dst),
        "expose_ports": expose_ports,
        "start_cmd": str(start_cmd),
        "runtime_deps": [str(dep) for dep in runtime_deps],
        "env_map": env_map,
        "copy_items": copy_items,
        "npm_install_block": npm_install_block,
        "pip_requirements_block": pip_requirements_block,
        "rdg_enable_ttyd": rdg_enable_ttyd,
        "rdg_ttyd_port": rdg_ttyd_port,
        "rdg_ttyd_login_cmd": rdg_ttyd_login_cmd,
        "output_dir": Path(args.output).resolve(),
        "inference_notes": inference_notes,
        "entry_file": infer_info.get("entry_file"),
    }


def render_files(context: Dict[str, Any]) -> None:
    stack_id = context["stack_id"]
    template_dir = TEMPLATES_DIR / stack_id
    docker_tpl_path = template_dir / "Dockerfile.tpl"
    start_tpl_path = template_dir / "start.sh.tpl"

    if not docker_tpl_path.exists() or not start_tpl_path.exists():
        raise ConfigError(f"模板不存在: {template_dir}")

    docker_tpl = load_template_with_includes(docker_tpl_path, TEMPLATES_DIR)
    start_tpl = load_template_with_includes(start_tpl_path, TEMPLATES_DIR)

    common_vars = {
        "BASE_IMAGE": context["base_image"],
        "WORKDIR": context["workdir"],
        "APP_SRC": context["app_src"],
        "APP_DST": context["app_dst"],
        "EXPOSE_PORTS": " ".join(context["expose_ports"]),
        "RUNTIME_DEPS_INSTALL": build_runtime_deps_install(
            context["runtime_deps"], context["base_image"]
        ),
        "COPY_APP": build_copy_app(context["copy_items"]),
        "START_CMD": context["start_cmd"],
        "NPM_INSTALL_BLOCK": build_npm_install_block(context.get("npm_install_block", "")),
        "PIP_REQUIREMENTS_BLOCK": build_pip_requirements_block(
            context.get("pip_requirements_block", "")
        ),
        "RDG_ENABLE_TTYD": "true" if context.get("rdg_enable_ttyd") else "false",
        "RDG_TTYD_PORT": context.get("rdg_ttyd_port", "8022"),
        "RDG_TTYD_LOGIN_CMD": context.get("rdg_ttyd_login_cmd", "/bin/bash"),
    }

    docker_vars = {
        **common_vars,
        "ENV_BLOCK": build_docker_env_lines(context["env_map"]),
    }

    start_vars = {
        **common_vars,
        "ENV_BLOCK": build_env_exports(context["env_map"]),
    }

    rendered_docker = render_template(docker_tpl, docker_vars)
    rendered_start = render_template(start_tpl, start_vars)

    validate_rendered(
        docker_text=rendered_docker,
        start_text=rendered_start,
        workdir=context["workdir"],
        start_mode=context["mode"],
    )

    out_dir: Path = context["output_dir"]
    out_dir.mkdir(parents=True, exist_ok=True)

    docker_out = out_dir / "Dockerfile"
    start_out = out_dir / "start.sh"
    flag_out = out_dir / "flag"

    docker_out.write_text(rendered_docker.rstrip() + "\n", encoding="utf-8")
    start_out.write_text(rendered_start.rstrip() + "\n", encoding="utf-8")

    os.chmod(start_out, 0o755)

    flag_default = "flag{static_test_flag}\n"
    if not flag_out.exists():
        flag_out.write_text(flag_default, encoding="utf-8")
    else:
        current = flag_out.read_text(encoding="utf-8", errors="ignore")
        if not current.strip() or current.strip().lower() == "flag{}":
            os.chmod(flag_out, 0o644)
            flag_out.write_text(flag_default, encoding="utf-8")
    os.chmod(flag_out, 0o444)

    print("生成完成（CloverSec-CTF-Build-Dockerizer）")
    print(f"- 输出目录: {out_dir}")
    print(f"- 技术栈: {context['stack_id']} ({context['stack_display']})")
    if context["auto_detected"]:
        print(f"- 栈来源: 自动侦测（置信度 {context['confidence'] * 100:.1f}%）")
    else:
        print("- 栈来源: 显式指定（config 或 CLI）")
    print(f"- 基础镜像: {context['base_image']}")
    print(f"- 端口: {' '.join(context['expose_ports'])}")
    print(f"- WORKDIR: {context['workdir']}")
    print(f"- 启动命令: {context['start_cmd']}")

    entry_file = context.get("entry_file")
    if entry_file:
        print(f"- 入口文件线索: {entry_file}")

    for note in context.get("inference_notes", []):
        prefix = "- 推断"
        if note.get("source") == "default":
            prefix = "- 【红色提示】"
        print(
            f"{prefix} {note['field']} = {note['value']} "
            f"（依据: {note.get('reason', '未提供')}，可通过 {note['override']} 覆盖）"
        )

    print("- 产物: Dockerfile, start.sh, flag")


def maybe_print_detect_debug(args: argparse.Namespace, details: List[Dict[str, Any]]) -> None:
    if not args.detect_debug:
        return

    print("栈侦测详情：")
    for item in details:
        print(
            "- {id}: score={score}/{max_score}, confidence={conf:.1f}%, file_hits={fh}, dir_hits={dh}".format(
                id=item["id"],
                score=item["score"],
                max_score=item["max_score"],
                conf=item["confidence"] * 100,
                fh=item["file_hits"],
                dh=item["dir_hits"],
            )
        )


def main() -> int:
    try:
        args = parse_args()
        stacks = load_stack_defs(DATA_DIR / "stacks.yaml")
        patterns = load_patterns(DATA_DIR / "patterns.yaml")
        context = build_render_context(args, stacks, patterns)
        maybe_print_detect_debug(args, context["detect_details"])
        render_files(context)
        return 0
    except ConfigError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
