#!/usr/bin/env python3
"""Platform contract normalization shared by audit, prepare and verify."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict


CONTRACT_DIRECT = "direct-exec-v1"
CONTRACT_LEGACY = "legacy-helper-v2"
CONTRACT_QEMU = "linux-qemu-v1"
FLAG_MODES = {
    "direct_exec",
    "file_replace",
    "database",
    "helper_script",
    "qemu_guest",
}


def _mapping(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def normalize_contract(challenge: Dict[str, Any] | None, project_dir: Path | None = None) -> Dict[str, Any]:
    """Return an explicit contract without changing the source configuration.

    The current platform writes the dynamic flag through ``docker exec``.
    Legacy helper scripts remain available only when explicitly requested.
    """

    challenge = _mapping(challenge)
    platform = _mapping(challenge.get("platform"))
    flag = _mapping(challenge.get("flag"))
    vm = _mapping(challenge.get("vm"))
    stack = str(challenge.get("stack") or "").strip().lower()

    explicit_contract = str(platform.get("contract") or "").strip().lower()
    explicit_mode = str(flag.get("mode") or "").strip().lower()
    if explicit_contract in {"legacy", "legacy-helper", CONTRACT_LEGACY}:
        contract = CONTRACT_LEGACY
    elif explicit_contract in {"qemu", CONTRACT_QEMU} or stack == "linux-qemu":
        contract = CONTRACT_QEMU
    else:
        contract = CONTRACT_DIRECT

    if explicit_mode:
        mode = explicit_mode
    elif contract == CONTRACT_LEGACY:
        mode = "helper_script"
    elif contract == CONTRACT_QEMU:
        mode = "qemu_guest"
    else:
        mode = "direct_exec"
    if mode not in FLAG_MODES:
        raise ValueError(f"unsupported flag.mode: {mode}")

    default_path = str(vm.get("guest_flag_path") or "/flag") if mode == "qemu_guest" else "/flag"
    path = str(flag.get("path") or default_path).strip() or default_path
    if not path.startswith("/"):
        raise ValueError(f"flag.path must be absolute: {path}")

    sync_paths = [str(item).strip() for item in flag.get("sync_paths", []) if str(item).strip()]
    if mode not in {"helper_script", "qemu_guest"}:
        sync_paths = []
    initial_file = flag.get("initial_file")
    if initial_file is None:
        initial_file = bool(project_dir and (project_dir / "flag").is_file())
    if isinstance(initial_file, str):
        initial_file = initial_file.strip().lower() in {"1", "true", "yes", "y"}

    update = _mapping(flag.get("update"))
    if mode not in {"file_replace", "database"}:
        update = {}
    require_bash = _bool(platform.get("require_bash"), mode in {"helper_script", "qemu_guest"})
    if mode in {"helper_script", "qemu_guest"}:
        require_bash = True
    return {
        "contract": contract,
        "entrypoint": str(platform.get("entrypoint") or "/start.sh"),
        "require_bash": require_bash,
        "flag": {
            "mode": mode,
            "path": path,
            "permission": str(flag.get("permission") or "444"),
            "initial_file": bool(initial_file),
            "sync_paths": sync_paths,
            "update": update,
        },
        "legacy_helper": mode in {"helper_script", "qemu_guest"},
        "source": "explicit" if explicit_contract or explicit_mode else "default",
    }


def contract_summary(contract: Dict[str, Any]) -> str:
    flag = contract.get("flag", {})
    return f"{contract.get('contract')} / {flag.get('mode')} / {flag.get('path')}"
