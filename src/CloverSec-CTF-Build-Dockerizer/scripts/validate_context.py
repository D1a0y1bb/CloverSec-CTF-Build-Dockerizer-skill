#!/usr/bin/env python3
"""Extract normalized V2 validation context from challenge.yaml."""

from __future__ import annotations

import shlex
import sys
from pathlib import Path


def pick_bool(source: dict, name: str, default: bool) -> str:
    value = source.get(name, default)
    if isinstance(value, str):
        value = value.strip().lower() in {"true", "1", "yes", "y"}
    return "true" if bool(value) else "false"


def main() -> int:
    if len(sys.argv) < 2:
        return 0

    try:
        import yaml
    except ModuleNotFoundError:
        print("CONFIG_CONTEXT_PARSE_FAILED: 缺少依赖 PyYAML", file=sys.stderr)
        return 2

    path = Path(sys.argv[1])
    if not path.is_file():
        print(f"CONFIG_CONTEXT_PARSE_FAILED: challenge.yaml 不存在: {path}", file=sys.stderr)
        return 2

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        print(f"CONFIG_CONTEXT_PARSE_FAILED: YAML 解析失败: {path}: {exc}", file=sys.stderr)
        return 2
    if not isinstance(raw, dict):
        print(f"CONFIG_CONTEXT_PARSE_FAILED: YAML 顶层必须是对象: {path}", file=sys.stderr)
        return 2
    challenge = raw.get("challenge") or {}
    if not isinstance(challenge, dict):
        print(f"CONFIG_CONTEXT_PARSE_FAILED: challenge 字段必须是对象: {path}", file=sys.stderr)
        return 2

    stack = str(challenge.get("stack") or "").strip()
    profile = str(challenge.get("profile") or "").strip().lower()
    if not profile:
        if stack == "rdg":
            profile = "rdg"
        elif stack == "secops":
            profile = "secops"
        else:
            profile = "jeopardy"

    defense = challenge.get("defense") if isinstance(challenge.get("defense"), dict) else {}
    legacy = challenge.get("rdg") if isinstance(challenge.get("rdg"), dict) else {}
    source = {**legacy, **defense}
    vm = challenge.get("vm") if isinstance(challenge.get("vm"), dict) else {}
    flag_cfg = challenge.get("flag") if isinstance(challenge.get("flag"), dict) else {}
    verification = challenge.get("verification") if isinstance(challenge.get("verification"), dict) else {}
    solve_probe = verification.get("solve_probe") if isinstance(verification.get("solve_probe"), dict) else {}
    sync_paths = flag_cfg.get("sync_paths") if isinstance(flag_cfg.get("sync_paths"), list) else []
    guest_forwards = vm.get("guest_forwards") if isinstance(vm.get("guest_forwards"), list) else []
    forward_host_ports = []
    for item in guest_forwards:
        if isinstance(item, dict):
            value = str(item.get("host_port") or "").strip()
            if value:
                forward_host_ports.append(value)

    scoring_mode = str(
        source.get("scoring_mode")
        or ("check_service" if profile in {"rdg", "awdp", "secops"} else "flag")
    ).strip().lower()
    include_flag = pick_bool(source, "include_flag_artifact", True)
    flag_optional = (
        "true"
        if profile in {"rdg", "awdp", "secops"} and include_flag == "false"
        else "false"
    )

    items = {
        "STACK_CFG": stack,
        "PROFILE_CFG": profile,
        "SUPPORT_LEVEL_CFG": str(challenge.get("support_level") or "supported").strip().lower(),
        "RDG_ENABLE_TTYD_CFG": pick_bool(source, "enable_ttyd", profile in {"rdg", "awd", "awdp", "secops"}),
        "RDG_ENABLE_SSHD_CFG": pick_bool(source, "enable_sshd", profile in {"rdg", "awd", "awdp", "secops"}),
        "RDG_SSHD_PASSWORD_AUTH_CFG": pick_bool(source, "sshd_password_auth", True),
        "RDG_TTYD_INSTALL_FALLBACK_CFG": pick_bool(source, "ttyd_install_fallback", True),
        "RDG_CTF_USER_CFG": str(source.get("ctf_user") or "ctf").strip(),
        "RDG_CTF_IN_ROOT_GROUP_CFG": pick_bool(source, "ctf_in_root_group", False),
        "RDG_SCORING_MODE_CFG": scoring_mode,
        "RDG_INCLUDE_FLAG_ARTIFACT_CFG": include_flag,
        "RDG_CHECK_ENABLED_CFG": pick_bool(source, "check_enabled", profile in {"rdg", "awdp", "secops"}),
        "RDG_CHECK_SCRIPT_PATH_CFG": str(source.get("check_script_path") or "check/check.sh").strip(),
        "RDG_WORKDIR_CFG": str(challenge.get("workdir") or "/app").strip(),
        "ALLOW_LOOPBACK_BIND_CFG": pick_bool(
            challenge.get("platform") if isinstance(challenge.get("platform"), dict) else {},
            "allow_loopback_bind",
            False,
        ),
        "FLAG_OPTIONAL_CFG": flag_optional,
        "START_CMD_CFG": str(((challenge.get("start") or {}).get("cmd")) or "").strip(),
        "FLAG_SYNC_PATHS_CFG": ",".join(str(item).strip() for item in sync_paths if str(item).strip()),
        "HAS_SOLVE_PROBE_CFG": "true" if bool(solve_probe) else "false",
        "VM_ACCELERATOR_CFG": str(vm.get("accelerator") or "tcg").strip().lower(),
        "VM_REQUIRE_KVM_CFG": pick_bool(vm, "require_kvm", False),
        "VM_KERNEL_CFG": str(vm.get("kernel") or "vm/vmlinuz").strip(),
        "VM_INITRD_CFG": str(vm.get("initrd") or "vm/initrd.img").strip(),
        "VM_ROOTFS_CFG": str(vm.get("rootfs") or "vm/rootfs.ext4").strip(),
        "VM_ASSET_MODE_CFG": str(vm.get("asset_mode") or "prebuilt").strip().lower(),
        "VM_FLAG_INJECTION_CFG": str(vm.get("flag_injection") or "debugfs").strip().lower(),
        "VM_GUEST_FLAG_PATH_CFG": str(vm.get("guest_flag_path") or "/root/flag").strip(),
        "VM_HOSTFWD_PORTS_CFG": ",".join(forward_host_ports),
    }

    for key, value in items.items():
        print(f"{key}={shlex.quote(value)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
