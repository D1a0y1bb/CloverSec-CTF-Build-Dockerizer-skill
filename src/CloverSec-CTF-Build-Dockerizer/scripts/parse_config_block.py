#!/usr/bin/env python3
"""解析 CONFIG PROPOSAL YAML 块并输出标准 challenge.yaml。"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any, Dict, Optional

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
DATA_DIR = SKILL_ROOT / "data"

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from utils import (  # noqa: E402
    ConfigError,
    ensure_dict,
    load_stack_defs,
    normalize_ports,
)

ALLOWED_STACKS = {"node", "php", "python", "java", "tomcat", "lamp", "pwn", "ai"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="从 stdin 读取 CONFIG PROPOSAL YAML 并转换为 challenge.yaml"
    )
    parser.add_argument("--output", default="challenge.yaml", help="输出 challenge.yaml 路径")
    parser.add_argument("--name", default="", help="challenge.name 覆盖值，默认按 stack 自动生成")
    return parser.parse_args()


def _load_yaml_module():
    try:
        import yaml
    except ModuleNotFoundError as exc:
        raise ConfigError(
            "缺少依赖 PyYAML。请先执行："
            "python3 -m pip install -r src/CloverSec-CTF-Build-Dockerizer/scripts/requirements.txt"
        ) from exc
    return yaml


def _extract_yaml_object(text: str, yaml_mod: Any) -> Dict[str, Any]:
    candidates = [text]

    code_blocks = re.findall(r"```(?:yaml|yml|json)?\s*(.*?)```", text, flags=re.IGNORECASE | re.DOTALL)
    candidates.extend(code_blocks)

    for idx, item in enumerate(candidates, start=1):
        chunk = item.strip()
        if not chunk:
            continue
        try:
            parsed = yaml_mod.safe_load(chunk)
        except Exception:
            continue
        if isinstance(parsed, dict):
            return parsed

    raise ConfigError(
        "YAML 解析失败：未识别到有效对象。请仅粘贴 CONFIG PROPOSAL YAML 块，"
        "或用 ```yaml ... ``` 包裹后重试。"
    )


def _extract_proposal(root: Dict[str, Any]) -> Dict[str, Any]:
    if "CONFIG PROPOSAL" in root:
        return ensure_dict(root.get("CONFIG PROPOSAL"), "CONFIG PROPOSAL")
    if "config_proposal" in root:
        return ensure_dict(root.get("config_proposal"), "config_proposal")

    # 兼容仅粘贴内部对象（不带外层键）
    if "stack" in root and "start" in root:
        return root

    raise ConfigError(
        "缺少 CONFIG PROPOSAL 根键。请回复“OK”或粘贴包含 `CONFIG PROPOSAL:` 的 YAML 块。"
    )


def _ensure_port_list(value: Any) -> list[str]:
    ports = normalize_ports(value)
    if not ports:
        return []

    for p in ports:
        if not p.isdigit():
            raise ConfigError(f"端口必须是数字：{p}")
        num = int(p)
        if num < 1 or num > 65535:
            raise ConfigError(f"端口超出范围（1-65535）：{p}")
    return ports


def _first_non_empty(*values: Any) -> Any:
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and value.strip() == "":
            continue
        return value
    return None


def _to_bool(value: Any, default: bool) -> bool:
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
    raise ConfigError(f"布尔字段解析失败：{value}")


def build_challenge(proposal: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    stacks = load_stack_defs(DATA_DIR / "stacks.yaml")

    stack_raw = str(_first_non_empty(proposal.get("stack"), "") or "").strip().lower()
    if not stack_raw:
        raise ConfigError("CONFIG PROPOSAL.stack 不能为空")
    if stack_raw not in ALLOWED_STACKS:
        raise ConfigError(f"不支持的 stack: {stack_raw}（允许: {', '.join(sorted(ALLOWED_STACKS))}）")
    if stack_raw not in stacks:
        raise ConfigError(f"stacks.yaml 未定义 stack: {stack_raw}")

    defaults = ensure_dict(stacks[stack_raw].get("defaults"), f"stacks.{stack_raw}.defaults")

    base_image = str(_first_non_empty(proposal.get("base_image"), defaults.get("base_image"), "") or "").strip()
    workdir = str(_first_non_empty(proposal.get("workdir"), defaults.get("workdir"), "/app") or "").strip()
    if not workdir:
        raise ConfigError("workdir 不能为空")

    app_src = str(_first_non_empty(proposal.get("app_src"), ".") or ".").strip() or "."
    app_dst = str(_first_non_empty(proposal.get("app_dst"), workdir) or workdir).strip() or workdir

    ports = _ensure_port_list(proposal.get("expose_ports"))
    if not ports:
        ports = _ensure_port_list(defaults.get("expose_ports"))
    if not ports:
        raise ConfigError("expose_ports 不能为空，请至少提供一个端口")

    start = ensure_dict(proposal.get("start"), "start")
    start_mode = str(_first_non_empty(start.get("mode"), "cmd") or "cmd").strip()
    if start_mode not in {"cmd", "service", "supervisor"}:
        raise ConfigError(f"start.mode 非法：{start_mode}（允许: cmd/service/supervisor）")

    default_cmd = str(defaults.get("start_cmd") or "").strip()
    start_cmd = str(_first_non_empty(start.get("cmd"), default_cmd, "") or "").strip()

    platform = ensure_dict(proposal.get("platform"), "platform")
    entrypoint = str(_first_non_empty(platform.get("entrypoint"), "/start.sh") or "/start.sh").strip()
    require_bash = _to_bool(platform.get("require_bash"), True)

    flag = ensure_dict(proposal.get("flag"), "flag")
    flag_path = str(_first_non_empty(flag.get("path"), "/flag") or "/flag").strip()
    flag_perm = str(_first_non_empty(flag.get("permission"), "444") or "444").strip()

    challenge_name = args.name.strip() if args.name.strip() else f"{stack_raw}-challenge"

    challenge: Dict[str, Any] = {
        "challenge": {
            "name": challenge_name,
            "stack": stack_raw,
            "base_image": base_image,
            "workdir": workdir,
            "app_src": app_src,
            "app_dst": app_dst,
            "expose_ports": ports,
            "start": {
                "mode": start_mode,
                "cmd": start_cmd,
            },
            "runtime_deps": [],
            "build_deps": [],
            "flag": {
                "path": flag_path,
                "permission": flag_perm,
            },
            "platform": {
                "entrypoint": entrypoint,
                "require_bash": require_bash,
            },
            "extra": {
                "env": {},
                "copy": [],
                "user": "",
            },
        }
    }
    return challenge


def write_yaml(data: Dict[str, Any], output: Path) -> None:
    yaml_mod = _load_yaml_module()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(yaml_mod.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")


def main() -> int:
    args = parse_args()
    raw_text = sys.stdin.read()
    if not raw_text.strip():
        print("[ERROR] 未从 stdin 读取到 CONFIG PROPOSAL 内容。", file=sys.stderr)
        return 2

    try:
        yaml_mod = _load_yaml_module()
        parsed = _extract_yaml_object(raw_text, yaml_mod)
        proposal = _extract_proposal(parsed)
        challenge_doc = build_challenge(proposal, args)
        output = Path(args.output).resolve()
        write_yaml(challenge_doc, output)
        print(f"[OK] 已生成 challenge.yaml: {output}")
        return 0
    except ConfigError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
