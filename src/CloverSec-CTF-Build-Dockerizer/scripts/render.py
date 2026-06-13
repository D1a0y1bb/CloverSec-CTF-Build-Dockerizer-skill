#!/usr/bin/env python3
"""将 challenge.yaml 或 CLI 参数渲染为 Dockerfile/start.sh/flag/changeflag。"""

from __future__ import annotations

import argparse
import contextlib
import gzip
import io
import os
import re
import shlex
import tarfile
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
DATA_DIR = SKILL_ROOT / "data"
TEMPLATES_DIR = SKILL_ROOT / "templates"
_DURATION_RE = re.compile(r"^[0-9]+(ns|us|ms|s|m|h)$")
_VM_MEMORY_RE = re.compile(r"^[0-9]+([KMGTP]i?B?|[kmg])?$")
_ALLOWED_VM_ACCELERATORS = {"auto", "tcg", "kvm"}
_ALLOWED_VM_ASSET_MODES = {"prebuilt", "build-script"}
_ALLOWED_VM_FLAG_INJECTIONS = {"debugfs", "none"}
_ALLOWED_VM_HEALTHCHECK_MODES = {"tcp", "ssh-banner", "ssh-auth-denied", "custom"}
_ALLOWED_VM_FORWARD_PROTOCOLS = {"tcp"}
_ALLOWED_VM_DRIVE_FORMATS = {"raw", "qcow2"}
_SAFE_TOKEN_RE = re.compile(r"^[A-Za-z0-9_.+-]+$")
_SAFE_QEMU_VALUE_RE = re.compile(r"^[A-Za-z0-9_.:/,=+-]+$")
_SAFE_REL_PATH_RE = re.compile(r"^[A-Za-z0-9_./@+=-]+$")
_SAFE_DOCKER_PLATFORM_RE = re.compile(r"^linux/[A-Za-z0-9_.-]+(/[A-Za-z0-9_.-]+)?$")
_SAFE_GUEST_ABS_PATH_RE = re.compile(r"^/[A-Za-z0-9_./@+=-]+$")
_SHELL_META_RE = re.compile(r"[$`\"'\\\n\r;&|<>]")
_DEFAULT_QEMU_BY_ARCH = {
    "x86_64": "qemu-system-x86_64",
    "amd64": "qemu-system-x86_64",
    "aarch64": "qemu-system-aarch64",
    "arm64": "qemu-system-aarch64",
}

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
    infer_runtime_profile_candidates,
    infer_from_patterns,
    load_patterns,
    load_profile_defs,
    load_runtime_profiles,
    load_stack_defs,
    load_template_with_includes,
    load_yaml_file,
    normalize_ports,
    render_template,
    resolve_runtime_profile_base_image,
    validate_rendered,
)
from audit_input import audit_project, proposal_gate_required  # noqa: E402
from result_utils import dump_json, read_json, sha256_file, structured_error, structured_ok  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="渲染 CTF Web Dockerfile/start.sh")
    parser.add_argument("--config", help="challenge.yaml 路径")

    parser.add_argument(
        "--stack",
        help="技术栈: node/php/python/java/tomcat/lamp/pwn/ai/rdg/secops/baseunit/linux-qemu",
    )
    parser.add_argument("--profile", choices=["jeopardy", "rdg", "awd", "awdp", "secops"], help="V2 profile")
    parser.add_argument("--port", action="append", help="暴露端口，可重复传入")
    parser.add_argument("--workdir", help="WORKDIR，默认取栈默认值")
    parser.add_argument("--start", dest="start_cmd", help="启动命令")
    parser.add_argument("--base-image", help="覆盖基础镜像")
    parser.add_argument("--runtime-profile", help="运行时档位（php/node/java），例如 php74-apache")
    parser.add_argument("--app-src", help="应用源码路径，默认 .")
    parser.add_argument("--app-dst", help="容器内应用路径，默认等于 WORKDIR")
    parser.add_argument("--mode", choices=["cmd", "service", "supervisor"], help="start.mode")
    parser.add_argument("--runtime-dep", action="append", default=[], help="额外运行依赖，可重复")
    parser.add_argument("--env", action="append", default=[], help="环境变量 KEY=VALUE，可重复")

    parser.add_argument("--output", default=".", help="输出目录，默认当前目录")
    parser.add_argument("--detect-debug", action="store_true", help="打印栈侦测详情")
    parser.add_argument("--format", choices=["text", "json"], default="text", help="输出格式")
    parser.add_argument("--manual", action="store_true", help="人工确认后绕过 proposal gate")
    parser.add_argument("--reason", default="", help="manual 绕过原因")
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


def build_file_plan(context: Dict[str, Any]) -> List[Dict[str, str]]:
    out_dir = Path(context["output_dir"])
    entries: List[tuple[str, str]] = [
        ("Dockerfile", "overwrite"),
        ("start.sh", "overwrite"),
        ("changeflag.sh", "overwrite"),
    ]
    if not bool(context.get("flag_optional", False)):
        entries.append(("flag", "create_or_preserve"))
    if context.get("rdg_check_enabled", True) and context.get("rdg_scoring_mode", "flag") == "check_service":
        entries.append((str(context.get("rdg_check_script_path", "check/check.sh")), "create_if_missing"))
    if context.get("profile") == "awdp":
        entries.extend(
            [
                ("patch/src/", "create_if_missing"),
                ("patch/patch.sh", "create_if_missing"),
                ("patch_bundle.tar.gz", "overwrite"),
            ]
        )
    plan: List[Dict[str, str]] = []
    for rel, action in entries:
        path = out_dir / rel.rstrip("/")
        plan.append(
            {
                "path": rel,
                "action": action,
                "exists": "true" if path.exists() else "false",
            }
        )
    return plan


def print_file_plan(plan: List[Dict[str, str]]) -> None:
    print("生成前文件计划")
    for item in plan:
        exists = "exists" if item["exists"] == "true" else "new"
        print(f"- {item['path']}: {item['action']} ({exists})")


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


def _merge_unique_ports(base_ports: List[str], extra_ports: List[str]) -> List[str]:
    merged = list(base_ports)
    seen = set(base_ports)
    for port in extra_ports:
        if port not in seen:
            merged.append(port)
            seen.add(port)
    return merged


def _parse_duration(value: Any, field_name: str, default: str) -> str:
    raw = str(first_non_empty(value, default) or default).strip()
    if not _DURATION_RE.match(raw):
        raise ConfigError(f"{field_name} 格式非法（示例: 30s/5s/10s）: {raw}")
    return raw


def _parse_positive_int(value: Any, field_name: str, default: int) -> int:
    if value is None:
        return default
    try:
        number = int(str(value).strip())
    except ValueError as exc:
        raise ConfigError(f"{field_name} 必须是正整数") from exc
    if number < 1:
        raise ConfigError(f"{field_name} 必须是正整数")
    return number


def _parse_port(value: Any, field_name: str, default: str) -> str:
    raw = str(first_non_empty(value, default) or default).strip()
    if not raw.isdigit() or not (1 <= int(raw) <= 65535):
        raise ConfigError(f"{field_name} 必须是 1-65535 的端口数字")
    return raw


def _clean_relpath(value: Any, field_name: str, default: str) -> str:
    raw = str(first_non_empty(value, default) or default).strip()
    if not raw:
        raise ConfigError(f"{field_name} 不能为空")
    path = Path(raw)
    if path.is_absolute() or ".." in path.parts:
        raise ConfigError(f"{field_name} 必须是相对路径，且不能包含 ..")
    if not _SAFE_REL_PATH_RE.match(raw) or _SHELL_META_RE.search(raw):
        raise ConfigError(f"{field_name} 包含不安全字符，仅支持字母、数字、点、斜杠、下划线、短横线、@、+、=")
    return raw


def _clean_optional_relpath(value: Any, field_name: str) -> str:
    if value is None:
        return ""
    raw = str(value).strip()
    if raw.lower() in {"", "none", "null", "false"}:
        return ""
    return _clean_relpath(raw, field_name, raw)


def _clean_token(value: Any, field_name: str, default: str, *, lower: bool = False) -> str:
    raw = str(first_non_empty(value, default) or default).strip()
    if lower:
        raw = raw.lower()
    if not raw or not _SAFE_TOKEN_RE.match(raw) or _SHELL_META_RE.search(raw):
        raise ConfigError(f"{field_name} 包含不安全字符")
    return raw


def _clean_qemu_value(value: Any, field_name: str, default: str) -> str:
    raw = str(first_non_empty(value, default) or default).strip()
    if not raw or not _SAFE_QEMU_VALUE_RE.match(raw) or _SHELL_META_RE.search(raw):
        raise ConfigError(f"{field_name} 包含不安全字符")
    return raw


def _clean_extra_args(value: Any, field_name: str) -> str:
    raw = str(first_non_empty(value, "") or "").strip()
    if not raw:
        return ""
    if _SHELL_META_RE.search(raw):
        raise ConfigError(f"{field_name} 包含 shell 元字符")
    try:
        shlex.split(raw)
    except ValueError as exc:
        raise ConfigError(f"{field_name} 参数格式非法: {exc}") from exc
    return raw


def _clean_guest_abs_path(value: Any, field_name: str, default: str) -> str:
    raw = str(first_non_empty(value, default) or default).strip()
    if not raw.startswith("/"):
        raise ConfigError(f"{field_name} 必须是 guest 内绝对路径")
    if not _SAFE_GUEST_ABS_PATH_RE.match(raw) or _SHELL_META_RE.search(raw) or ".." in Path(raw).parts:
        raise ConfigError(f"{field_name} 包含不安全字符")
    return raw


def _clean_docker_platform(value: Any, field_name: str) -> str:
    raw = str(first_non_empty(value, "") or "").strip()
    if not raw:
        return ""
    if not _SAFE_DOCKER_PLATFORM_RE.match(raw) or _SHELL_META_RE.search(raw):
        raise ConfigError(f"{field_name} 格式非法，示例：linux/amd64 或 linux/arm64")
    return raw


def _normalize_flag_sync_paths(value: Any) -> List[str]:
    if value is None:
        return []
    items = ensure_list(value, "challenge.flag.sync_paths")
    paths: List[str] = []
    for idx, item in enumerate(items, start=1):
        raw = str(item).strip()
        if not raw:
            raise ConfigError(f"challenge.flag.sync_paths 第 {idx} 项不能为空")
        _clean_guest_abs_path(raw, f"challenge.flag.sync_paths[{idx}]", raw)
        if raw not in paths:
            paths.append(raw)
    return paths


def _normalize_vm_guest_forwards(value: Any, expose_ports: List[str]) -> List[Dict[str, str]]:
    if value is None:
        default_port = expose_ports[0] if expose_ports else "22"
        return [{"proto": "tcp", "host_port": default_port, "guest_port": default_port}]

    items = ensure_list(value, "challenge.vm.guest_forwards")
    forwards: List[Dict[str, str]] = []
    for idx, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            raise ConfigError(f"challenge.vm.guest_forwards 第 {idx} 项必须是对象")
        proto = str(first_non_empty(item.get("proto"), "tcp") or "tcp").strip().lower()
        if proto not in _ALLOWED_VM_FORWARD_PROTOCOLS:
            raise ConfigError(f"challenge.vm.guest_forwards 第 {idx} 项 proto 仅支持 tcp")
        host_port = _parse_port(item.get("host_port"), f"challenge.vm.guest_forwards[{idx}].host_port", "22")
        guest_port = _parse_port(item.get("guest_port"), f"challenge.vm.guest_forwards[{idx}].guest_port", host_port)
        forwards.append({"proto": proto, "host_port": host_port, "guest_port": guest_port})

    if not forwards:
        raise ConfigError("challenge.vm.guest_forwards 不能为空")
    return forwards


def _build_vm_netdev(forwards: List[Dict[str, str]], netdev_id: str) -> str:
    parts = ["user", f"id={netdev_id}"]
    for item in forwards:
        parts.append(
            "hostfwd={proto}::{host_port}-:{guest_port}".format(
                proto=item["proto"],
                host_port=item["host_port"],
                guest_port=item["guest_port"],
            )
        )
    return ",".join(parts)


def _format_vm_forwards(forwards: List[Dict[str, str]]) -> str:
    return " ".join(
        f'{item["proto"]}:{item["host_port"]}->{item["guest_port"]}' for item in forwards
    )


def _quote_shell(value: str) -> str:
    return shlex.quote(str(value))


def _render_flag_sync_block(sync_paths: List[str]) -> str:
    if not sync_paths:
        return ""
    quoted = " ".join(shlex.quote(path) for path in sync_paths)
    return (
        "\n"
        "if [[ \"${CTFBUILD_SKIP_SYNC_PATHS:-0}\" != \"1\" ]]; then\n"
        f"  FLAG_SYNC_PATHS=({quoted})\n"
        "  for sync_path in \"${FLAG_SYNC_PATHS[@]}\"; do\n"
        "    if [[ -z \"${sync_path}\" ]]; then\n"
        "      continue\n"
        "    fi\n"
        "    mkdir -p \"$(dirname \"${sync_path}\")\"\n"
        "    printf '%s\\n' \"${TARGET_FLAG}\" > \"${sync_path}\"\n"
        "    chmod 444 \"${sync_path}\" || true\n"
        "    echo \"[INFO] flag synced to ${sync_path}\"\n"
        "  done\n"
        "fi\n"
    )


def _vm_default_healthcheck_cmd(mode: str, host_port: str) -> str:
    if mode == "tcp":
        return f"bash -lc 'echo > /dev/tcp/127.0.0.1/{host_port}'"
    if mode == "ssh-banner":
        return (
            "bash -lc 'timeout 8 bash -c "
            f"\"cat < /dev/tcp/127.0.0.1/{host_port}\" | head -c 4 | grep -q SSH-'"
        )
    if mode == "ssh-auth-denied":
        return (
            "bash -lc 'ssh -o BatchMode=yes -o StrictHostKeyChecking=no "
            "-o UserKnownHostsFile=/dev/null -o ConnectTimeout=5 "
            f"-p {host_port} 127.0.0.1 true 2>&1 | grep -Eqi \"Permission denied|denied\"'"
        )
    raise ConfigError("challenge.vm.healthcheck_mode=custom 时必须显式提供 challenge.healthcheck.cmd")


def _normalize_vm_config(vm_cfg: Dict[str, Any], expose_ports: List[str]) -> Dict[str, Any]:
    arch = _clean_token(vm_cfg.get("arch"), "challenge.vm.arch", "x86_64", lower=True)
    qemu_binary = _clean_token(
        first_non_empty(vm_cfg.get("qemu_binary"), _DEFAULT_QEMU_BY_ARCH.get(arch), "qemu-system-x86_64")
        or "qemu-system-x86_64",
        "challenge.vm.qemu_binary",
        "qemu-system-x86_64",
    )
    if not qemu_binary.startswith("qemu-system-"):
        raise ConfigError("challenge.vm.qemu_binary 必须是 qemu-system-*")

    accelerator = str(first_non_empty(vm_cfg.get("accelerator"), "tcg") or "tcg").strip().lower()
    if accelerator not in _ALLOWED_VM_ACCELERATORS:
        raise ConfigError("challenge.vm.accelerator 仅支持 auto/tcg/kvm")

    memory = str(first_non_empty(vm_cfg.get("memory"), "768M") or "768M").strip()
    if not _VM_MEMORY_RE.match(memory):
        raise ConfigError("challenge.vm.memory 格式非法，示例：768M/1G/1024")

    cpus = _parse_positive_int(vm_cfg.get("cpus"), "challenge.vm.cpus", 2)
    if cpus > 16:
        raise ConfigError("challenge.vm.cpus 不建议超过 16")

    asset_mode = str(first_non_empty(vm_cfg.get("asset_mode"), "prebuilt") or "prebuilt").strip().lower()
    if asset_mode not in _ALLOWED_VM_ASSET_MODES:
        raise ConfigError("challenge.vm.asset_mode 仅支持 prebuilt/build-script")

    flag_injection = str(first_non_empty(vm_cfg.get("flag_injection"), "debugfs") or "debugfs").strip().lower()
    if flag_injection not in _ALLOWED_VM_FLAG_INJECTIONS:
        raise ConfigError("challenge.vm.flag_injection 仅支持 debugfs/none")

    healthcheck_mode = str(first_non_empty(vm_cfg.get("healthcheck_mode"), "ssh-banner") or "ssh-banner").strip().lower()
    if healthcheck_mode not in _ALLOWED_VM_HEALTHCHECK_MODES:
        raise ConfigError("challenge.vm.healthcheck_mode 仅支持 tcp/ssh-banner/ssh-auth-denied/custom")

    netdev_id = str(first_non_empty(vm_cfg.get("netdev_id"), "net0") or "net0").strip()
    if not re.match(r"^[A-Za-z0-9_.-]+$", netdev_id):
        raise ConfigError("challenge.vm.netdev_id 只能包含字母、数字、点、下划线和短横线")

    forwards = _normalize_vm_guest_forwards(vm_cfg.get("guest_forwards"), expose_ports)
    hostfwd_ports = [item["host_port"] for item in forwards]

    rootfs = _clean_relpath(vm_cfg.get("rootfs"), "challenge.vm.rootfs", "vm/rootfs.ext4")
    drive_format = _clean_token(vm_cfg.get("drive_format"), "challenge.vm.drive_format", "raw", lower=True)
    if drive_format not in _ALLOWED_VM_DRIVE_FORMATS:
        raise ConfigError("challenge.vm.drive_format 仅支持 raw/qcow2")

    guest_flag_path = _clean_guest_abs_path(vm_cfg.get("guest_flag_path"), "challenge.vm.guest_flag_path", "/root/flag")

    if "initrd" in vm_cfg:
        initrd = _clean_optional_relpath(vm_cfg.get("initrd"), "challenge.vm.initrd")
    else:
        initrd = _clean_relpath(None, "challenge.vm.initrd", "vm/initrd.img")

    normalized = {
        "arch": arch,
        "qemu_binary": qemu_binary,
        "machine": _clean_qemu_value(vm_cfg.get("machine"), "challenge.vm.machine", "q35"),
        "accelerator": accelerator,
        "require_kvm": _to_bool(vm_cfg.get("require_kvm"), "challenge.vm.require_kvm", False),
        "cpu": _clean_qemu_value(vm_cfg.get("cpu"), "challenge.vm.cpu", "max"),
        "memory": memory,
        "cpus": str(cpus),
        "kernel": _clean_relpath(vm_cfg.get("kernel"), "challenge.vm.kernel", "vm/vmlinuz"),
        "initrd": initrd,
        "rootfs": rootfs,
        "drive_format": drive_format,
        "append": str(
            first_non_empty(
                vm_cfg.get("append"),
                "console=ttyS0 root=/dev/vda rw init=/sbin/init panic=-1",
            )
            or ""
        ).strip(),
        "netdev_id": netdev_id,
        "net_device": _clean_qemu_value(vm_cfg.get("net_device"), "challenge.vm.net_device", "e1000"),
        "guest_forwards": forwards,
        "hostfwd_ports": hostfwd_ports,
        "netdev": _build_vm_netdev(forwards, netdev_id),
        "monitor": _clean_qemu_value(vm_cfg.get("monitor"), "challenge.vm.monitor", "none"),
        "extra_args": _clean_extra_args(vm_cfg.get("extra_args"), "challenge.vm.extra_args"),
        "asset_mode": asset_mode,
        "build_script": _clean_relpath(vm_cfg.get("build_script"), "challenge.vm.build_script", "scripts/build-vm.sh"),
        "guest_flag_path": guest_flag_path,
        "flag_injection": flag_injection,
        "healthcheck_mode": healthcheck_mode,
    }
    return normalized


def _resolve_rdg_check_host_path(output_dir: Path, workdir: str, check_script_path: str) -> Path:
    raw = str(check_script_path).strip()
    if not raw:
        raise ConfigError("challenge.rdg.check_script_path 不能为空")

    if raw.startswith("/"):
        workdir_norm = workdir.rstrip("/")
        if workdir_norm and raw.startswith(workdir_norm + "/"):
            rel = raw[len(workdir_norm) + 1 :]
        else:
            rel = raw.lstrip("/")
    else:
        rel = raw

    rel = rel.strip("/")
    if not rel:
        raise ConfigError("challenge.rdg.check_script_path 不能为空路径根")
    return output_dir / rel


def _normalize_tarinfo(info: tarfile.TarInfo) -> tarfile.TarInfo:
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    info.mtime = 0
    if info.isdir():
        info.mode = 0o755
    elif info.isfile():
        info.mode = 0o755 if (info.mode & 0o111) else 0o644
    return info


def _build_deterministic_patch_bundle(patch_bundle: Path, patch_script: Path, patch_src: Path) -> None:
    def _dir_info(name: str) -> tarfile.TarInfo:
        info = tarfile.TarInfo(name)
        info.type = tarfile.DIRTYPE
        info.mode = 0o755
        info.size = 0
        return _normalize_tarinfo(info)

    patch_bundle.parent.mkdir(parents=True, exist_ok=True)
    with patch_bundle.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0, filename="") as gz:
            with tarfile.open(fileobj=gz, mode="w", format=tarfile.GNU_FORMAT) as tar:
                tar.addfile(_dir_info("patch"))
                tar.addfile(_dir_info("patch/src"))

                patch_script_info = _normalize_tarinfo(
                    tar.gettarinfo(str(patch_script), arcname="patch/patch.sh")
                )
                with patch_script.open("rb") as fh:
                    tar.addfile(patch_script_info, fh)

                for child in sorted(patch_src.rglob("*"), key=lambda p: p.relative_to(patch_src).as_posix()):
                    rel = child.relative_to(patch_src).as_posix()
                    arcname = f"patch/src/{rel}"
                    if child.is_dir():
                        tar.addfile(_normalize_tarinfo(tar.gettarinfo(str(child), arcname=arcname)))
                        continue
                    if child.is_file():
                        info = _normalize_tarinfo(tar.gettarinfo(str(child), arcname=arcname))
                        with child.open("rb") as fh:
                            tar.addfile(info, fh)


def _default_profile_for_stack(stack_id: str) -> str:
    if stack_id == "rdg":
        return "rdg"
    if stack_id == "secops":
        return "secops"
    return "jeopardy"


def _normalize_profile(value: Any, stack_id: str) -> str:
    raw = str(first_non_empty(value, _default_profile_for_stack(stack_id)) or "").strip().lower()
    if raw not in {"jeopardy", "rdg", "awd", "awdp", "secops"}:
        raise ConfigError(f"challenge.profile 不支持: {raw}")
    return raw


def _default_defense_config(profile_defs: Dict[str, Any], profile: str, stack_id: str) -> Dict[str, Any]:
    profiles = ensure_dict(profile_defs.get("profiles"), "profiles")
    profile_defaults = ensure_dict(profiles.get(profile), f"profiles.{profile}")
    return {
        "enable_ttyd": bool(first_non_empty(profile_defaults.get("enable_ttyd"), False)),
        "ttyd_port": str(first_non_empty(profile_defaults.get("ttyd_port"), "8022")),
        "ttyd_login_cmd": str(first_non_empty(profile_defaults.get("ttyd_login_cmd"), "/bin/bash")),
        "enable_sshd": bool(first_non_empty(profile_defaults.get("enable_sshd"), False)),
        "sshd_port": str(first_non_empty(profile_defaults.get("sshd_port"), "22")),
        "sshd_password_auth": bool(first_non_empty(profile_defaults.get("sshd_password_auth"), True)),
        "ttyd_binary_relpath": str(first_non_empty(profile_defaults.get("ttyd_binary_relpath"), "ttyd")),
        "ttyd_install_fallback": bool(first_non_empty(profile_defaults.get("ttyd_install_fallback"), True)),
        "ctf_user": str(first_non_empty(profile_defaults.get("ctf_user"), "ctf")),
        "ctf_password": str(first_non_empty(profile_defaults.get("ctf_password"), "123456")),
        "ctf_in_root_group": bool(first_non_empty(profile_defaults.get("ctf_in_root_group"), False)),
        "scoring_mode": str(first_non_empty(profile_defaults.get("scoring_mode"), "flag")),
        "include_flag_artifact": bool(first_non_empty(profile_defaults.get("include_flag_artifact"), True)),
        "check_enabled": bool(first_non_empty(profile_defaults.get("check_enabled"), False)),
        "check_script_path": str(first_non_empty(profile_defaults.get("check_script_path"), "check/check.sh")),
    }


def _normalize_defense_config(
    profile_defs: Dict[str, Any],
    stack_id: str,
    profile: str,
    defense_cfg: Dict[str, Any],
    legacy_rdg_cfg: Dict[str, Any],
) -> Dict[str, Any]:
    source = {**legacy_rdg_cfg, **defense_cfg}
    merged = _default_defense_config(profile_defs, profile, stack_id)
    merged["enable_ttyd"] = _to_bool(source.get("enable_ttyd"), "challenge.defense.enable_ttyd", merged["enable_ttyd"])
    ttyd_port_raw = first_non_empty(source.get("ttyd_port"), merged["ttyd_port"])
    merged["ttyd_port"] = str(ttyd_port_raw).strip()
    if not merged["ttyd_port"].isdigit() or not (1 <= int(merged["ttyd_port"]) <= 65535):
        raise ConfigError("challenge.defense.ttyd_port 必须是 1-65535 的端口数字")

    merged["ttyd_login_cmd"] = str(first_non_empty(source.get("ttyd_login_cmd"), merged["ttyd_login_cmd"])).strip()
    if not merged["ttyd_login_cmd"]:
        raise ConfigError("challenge.defense.ttyd_login_cmd 不能为空")

    merged["enable_sshd"] = _to_bool(source.get("enable_sshd"), "challenge.defense.enable_sshd", merged["enable_sshd"])
    sshd_port_raw = first_non_empty(source.get("sshd_port"), merged["sshd_port"])
    merged["sshd_port"] = str(sshd_port_raw).strip()
    if not merged["sshd_port"].isdigit() or not (1 <= int(merged["sshd_port"]) <= 65535):
        raise ConfigError("challenge.defense.sshd_port 必须是 1-65535 的端口数字")

    merged["sshd_password_auth"] = _to_bool(
        source.get("sshd_password_auth"),
        "challenge.defense.sshd_password_auth",
        merged["sshd_password_auth"],
    )
    merged["ttyd_binary_relpath"] = str(
        first_non_empty(source.get("ttyd_binary_relpath"), merged["ttyd_binary_relpath"])
    ).strip()
    if not merged["ttyd_binary_relpath"]:
        raise ConfigError("challenge.defense.ttyd_binary_relpath 不能为空")
    merged["ttyd_install_fallback"] = _to_bool(
        source.get("ttyd_install_fallback"),
        "challenge.defense.ttyd_install_fallback",
        merged["ttyd_install_fallback"],
    )
    merged["ctf_user"] = str(first_non_empty(source.get("ctf_user"), merged["ctf_user"])).strip()
    if not merged["ctf_user"]:
        raise ConfigError("challenge.defense.ctf_user 不能为空")
    merged["ctf_password"] = str(first_non_empty(source.get("ctf_password"), merged["ctf_password"])).strip()
    if not merged["ctf_password"]:
        raise ConfigError("challenge.defense.ctf_password 不能为空")
    merged["ctf_in_root_group"] = _to_bool(
        source.get("ctf_in_root_group"),
        "challenge.defense.ctf_in_root_group",
        merged["ctf_in_root_group"],
    )
    merged["scoring_mode"] = str(first_non_empty(source.get("scoring_mode"), merged["scoring_mode"])).strip().lower()
    if merged["scoring_mode"] not in {"check_service", "flag"}:
        raise ConfigError("challenge.defense.scoring_mode 仅支持 check_service 或 flag")
    merged["include_flag_artifact"] = _to_bool(
        source.get("include_flag_artifact"),
        "challenge.defense.include_flag_artifact",
        merged["include_flag_artifact"],
    )
    merged["check_enabled"] = _to_bool(
        source.get("check_enabled"),
        "challenge.defense.check_enabled",
        merged["check_enabled"],
    )
    merged["check_script_path"] = str(
        first_non_empty(source.get("check_script_path"), merged["check_script_path"])
    ).strip()
    if merged["check_enabled"] and not merged["check_script_path"]:
        raise ConfigError("challenge.defense.check_script_path 不能为空")
    return merged


def build_render_context(
    args: argparse.Namespace,
    stacks: Dict[str, Dict[str, Any]],
    patterns_data: Dict[str, Any],
    profile_defs: Dict[str, Any],
    runtime_profiles_data: Dict[str, Any],
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
    platform_cfg = ensure_dict(challenge.get("platform"), "challenge.platform")
    healthcheck_cfg = ensure_dict(challenge.get("healthcheck"), "challenge.healthcheck")
    flag_cfg = ensure_dict(challenge.get("flag"), "challenge.flag")
    verification_cfg = ensure_dict(challenge.get("verification"), "challenge.verification")
    extra_cfg = ensure_dict(challenge.get("extra"), "challenge.extra")
    defense_cfg = ensure_dict(challenge.get("defense"), "challenge.defense")
    rdg_cfg = ensure_dict(challenge.get("rdg"), "challenge.rdg")
    profile = _normalize_profile(first_non_empty(args.profile, challenge.get("profile")), stack_id)
    normalized_defense = _normalize_defense_config(profile_defs, stack_id, profile, defense_cfg, rdg_cfg)

    mode = first_non_empty(args.mode, start_cfg.get("mode"), "cmd")
    if mode not in {"cmd", "service", "supervisor"}:
        raise ConfigError(f"不支持的 start.mode: {mode}")

    infer_info = infer_from_patterns(scan_dir, stack_id, patterns_data)
    runtime_info = infer_runtime_profile_candidates(scan_dir, stack_id, runtime_profiles_data)

    rdg_enable_ttyd = bool(normalized_defense["enable_ttyd"])
    rdg_ttyd_port = str(normalized_defense["ttyd_port"])
    rdg_ttyd_login_cmd = str(normalized_defense["ttyd_login_cmd"])
    rdg_enable_sshd = bool(normalized_defense["enable_sshd"])
    rdg_sshd_port = str(normalized_defense["sshd_port"])
    rdg_sshd_password_auth = bool(normalized_defense["sshd_password_auth"])
    rdg_ttyd_binary_relpath = str(normalized_defense["ttyd_binary_relpath"])
    rdg_ttyd_install_fallback = bool(normalized_defense["ttyd_install_fallback"])
    rdg_ctf_user = str(normalized_defense["ctf_user"])
    rdg_ctf_password = str(normalized_defense["ctf_password"])
    rdg_ctf_in_root_group = bool(normalized_defense["ctf_in_root_group"])
    rdg_scoring_mode = str(normalized_defense["scoring_mode"])
    rdg_include_flag_artifact = bool(normalized_defense["include_flag_artifact"])
    rdg_check_enabled = bool(normalized_defense["check_enabled"])
    rdg_check_script_path = str(normalized_defense["check_script_path"])

    inferred_base_image_raw = infer_info.get("base_image")
    inferred_base_image = (
        inferred_base_image_raw.strip() if isinstance(inferred_base_image_raw, str) else ""
    )

    allow_loopback_bind = _to_bool(
        platform_cfg.get("allow_loopback_bind"), "challenge.platform.allow_loopback_bind", False
    )
    docker_platform = _clean_docker_platform(
        platform_cfg.get("docker_platform"), "challenge.platform.docker_platform"
    )

    default_healthcheck_cmd = str(defaults.get("healthcheck_cmd") or "").strip()
    healthcheck_enabled = _to_bool(
        healthcheck_cfg.get("enabled"), "challenge.healthcheck.enabled", True
    )
    healthcheck_cmd = str(
        first_non_empty(healthcheck_cfg.get("cmd"), default_healthcheck_cmd, "") or ""
    ).strip()
    if healthcheck_enabled and not healthcheck_cmd:
        raise ConfigError("challenge.healthcheck.enabled=true 时，challenge.healthcheck.cmd 不能为空")
    healthcheck_interval = _parse_duration(
        healthcheck_cfg.get("interval"), "challenge.healthcheck.interval", "30s"
    )
    healthcheck_timeout = _parse_duration(
        healthcheck_cfg.get("timeout"), "challenge.healthcheck.timeout", "5s"
    )
    healthcheck_retries = _parse_positive_int(
        healthcheck_cfg.get("retries"), "challenge.healthcheck.retries", 3
    )
    healthcheck_start_period = _parse_duration(
        healthcheck_cfg.get("start_period"), "challenge.healthcheck.start_period", "10s"
    )

    runtime_profile_selected = ""
    runtime_base_image = ""
    runtime_profile_source = ""
    if args.runtime_profile:
        runtime_profile_selected = str(args.runtime_profile).strip()
        if runtime_profile_selected:
            runtime_base_image = resolve_runtime_profile_base_image(
                runtime_profiles_data, stack_id, runtime_profile_selected
            )
            runtime_profile_source = "cli"
    elif _has_value(challenge.get("runtime_profile")):
        runtime_profile_selected = str(challenge.get("runtime_profile")).strip()
        runtime_base_image = resolve_runtime_profile_base_image(
            runtime_profiles_data, stack_id, runtime_profile_selected
        )
        runtime_profile_source = "challenge"
    elif runtime_info.get("supported"):
        runtime_profile_selected = str(runtime_info.get("recommended_profile", "")).strip()
        runtime_base_image = str(runtime_info.get("recommended_base_image", "")).strip()
        runtime_profile_source = "inference"

    cfg_base_image = str(challenge.get("base_image") or "").strip()
    cli_runtime_base = runtime_base_image if runtime_profile_source == "cli" else ""
    cfg_runtime_base = runtime_base_image if runtime_profile_source == "challenge" else ""
    inferred_runtime_base = runtime_base_image if runtime_profile_source == "inference" else ""

    base_image = first_non_empty(
        args.base_image,
        cli_runtime_base,
        cfg_base_image,
        cfg_runtime_base,
        inferred_runtime_base,
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

    if profile != "jeopardy":
        rdg_extra_ports: List[str] = []
        if rdg_enable_ttyd:
            rdg_extra_ports.append(rdg_ttyd_port)
        if rdg_enable_sshd:
            rdg_extra_ports.append(rdg_sshd_port)
        expose_ports = _merge_unique_ports(expose_ports, rdg_extra_ports)

    if not expose_ports:
        raise ConfigError("expose_ports 不能为空，至少需要一个端口")

    vm_config: Dict[str, Any] = {}
    if stack_id == "linux-qemu":
        vm_cfg = ensure_dict(challenge.get("vm"), "challenge.vm")
        vm_config = _normalize_vm_config(vm_cfg, expose_ports)
        missing_forward_ports = [
            port for port in vm_config["hostfwd_ports"] if port not in expose_ports
        ]
        if missing_forward_ports:
            raise ConfigError(
                "challenge.vm.guest_forwards.host_port 必须出现在 challenge.expose_ports: "
                + ", ".join(missing_forward_ports)
            )
        if healthcheck_enabled and not _has_value(healthcheck_cfg.get("cmd")):
            health_port = vm_config["hostfwd_ports"][0]
            healthcheck_cmd = _vm_default_healthcheck_cmd(vm_config["healthcheck_mode"], health_port)

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

    if not args.base_image and runtime_profile_selected and runtime_base_image:
        inference_notes.append(
            {
                "field": "runtime_profile",
                "value": runtime_profile_selected,
                "source": runtime_profile_source or "inference",
                "reason": "运行时档位映射到基础镜像；若同时配置 challenge.base_image，以 challenge.base_image 为准",
                "override": "--runtime-profile / --base-image / challenge.base_image",
            }
        )

    if (
        not args.base_image
        and not cfg_base_image
        and not cli_runtime_base
        and not cfg_runtime_base
        and not inferred_runtime_base
    ):
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
    flag_sync_paths = _normalize_flag_sync_paths(flag_cfg.get("sync_paths"))
    solve_probe = ensure_dict(verification_cfg.get("solve_probe"), "challenge.verification.solve_probe")

    return {
        "stack_id": stack_id,
        "stack_display": stack_info.get("display_name", stack_id),
        "profile": profile,
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
        "flag_sync_paths": flag_sync_paths,
        "solve_probe": solve_probe,
        "rdg_enable_ttyd": rdg_enable_ttyd,
        "rdg_ttyd_port": rdg_ttyd_port,
        "rdg_ttyd_login_cmd": rdg_ttyd_login_cmd,
        "rdg_enable_sshd": rdg_enable_sshd,
        "rdg_sshd_port": rdg_sshd_port,
        "rdg_sshd_password_auth": rdg_sshd_password_auth,
        "rdg_ttyd_binary_relpath": rdg_ttyd_binary_relpath,
        "rdg_ttyd_install_fallback": rdg_ttyd_install_fallback,
        "rdg_ctf_user": rdg_ctf_user,
        "rdg_ctf_password": rdg_ctf_password,
        "rdg_ctf_in_root_group": rdg_ctf_in_root_group,
        "rdg_scoring_mode": rdg_scoring_mode,
        "rdg_include_flag_artifact": rdg_include_flag_artifact,
        "rdg_check_enabled": rdg_check_enabled,
        "rdg_check_script_path": rdg_check_script_path,
        "defense_enabled": profile != "jeopardy" and (rdg_enable_ttyd or rdg_enable_sshd),
        "flag_optional": profile in {"rdg", "awdp", "secops"} and not rdg_include_flag_artifact,
        "allow_loopback_bind": allow_loopback_bind,
        "docker_platform": docker_platform,
        "healthcheck_enabled": healthcheck_enabled,
        "healthcheck_cmd": healthcheck_cmd,
        "healthcheck_interval": healthcheck_interval,
        "healthcheck_timeout": healthcheck_timeout,
        "healthcheck_retries": healthcheck_retries,
        "healthcheck_start_period": healthcheck_start_period,
        "vm": vm_config,
        "output_dir": Path(args.output).resolve(),
        "inference_notes": inference_notes,
        "entry_file": infer_info.get("entry_file"),
        "runtime_supported": bool(runtime_info.get("supported", False)),
        "runtime_profile_selected": runtime_profile_selected,
        "runtime_profile_source": runtime_profile_source,
        "runtime_profile_candidates": runtime_info.get("candidates", []),
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

    flag_docker_block = load_template_with_includes(
        TEMPLATES_DIR / "snippets" / "copy-flag-start.tpl", TEMPLATES_DIR
    ).rstrip()
    flag_start_block = load_template_with_includes(
        TEMPLATES_DIR / "snippets" / "ensure-flag.tpl", TEMPLATES_DIR
    ).rstrip()

    if context.get("flag_optional", False):
        flag_docker_block = (
            "# profile allow flag_optional：跳过 /flag 产物拷贝。"
            "\nCOPY start.sh /start.sh"
            "\nCOPY changeflag.sh /changeflag.sh"
            "\nRUN chmod 555 /start.sh"
            "\nRUN chmod 555 /changeflag.sh"
        )
        flag_start_block = ": # profile flag_optional=true：跳过 /flag 检查"

    healthcheck_block = "# healthcheck disabled"
    if context.get("healthcheck_enabled", True):
        health_tpl = load_template_with_includes(
            TEMPLATES_DIR / "snippets" / "healthcheck.tpl", TEMPLATES_DIR
        )
        healthcheck_block = render_template(
            health_tpl,
            {
                "HEALTHCHECK_INTERVAL": str(context.get("healthcheck_interval", "30s")),
                "HEALTHCHECK_TIMEOUT": str(context.get("healthcheck_timeout", "5s")),
                "HEALTHCHECK_RETRIES": str(context.get("healthcheck_retries", 3)),
                "HEALTHCHECK_START_PERIOD": str(context.get("healthcheck_start_period", "10s")),
                "HEALTHCHECK_CMD": str(context.get("healthcheck_cmd", "")),
            },
        ).rstrip()

    defense_docker_block = "# defense block disabled"
    defense_start_block = ": # defense block disabled"
    if context["stack_id"] not in {"rdg", "secops"} and context.get("defense_enabled", False):
        defense_docker_tpl = load_template_with_includes(
            TEMPLATES_DIR / "snippets" / "defense-docker-block.tpl", TEMPLATES_DIR
        )
        defense_start_tpl = load_template_with_includes(
            TEMPLATES_DIR / "snippets" / "defense-start-block.tpl", TEMPLATES_DIR
        )
        defense_docker_block = render_template(defense_docker_tpl, common_vars := {
            "BASE_IMAGE": context["base_image"],
            "DOCKER_FROM_PLATFORM": f"--platform={context.get('docker_platform')} " if context.get("docker_platform") else "",
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
            "RDG_ENABLE_SSHD": "true" if context.get("rdg_enable_sshd") else "false",
            "RDG_SSHD_PORT": context.get("rdg_sshd_port", "22"),
            "RDG_SSHD_PASSWORD_AUTH_TEXT": "yes"
            if context.get("rdg_sshd_password_auth", True)
            else "no",
            "RDG_TTYD_BINARY_RELPATH": context.get("rdg_ttyd_binary_relpath", "ttyd"),
            "RDG_TTYD_INSTALL_FALLBACK": "true"
            if context.get("rdg_ttyd_install_fallback", True)
            else "false",
            "RDG_CTF_USER": context.get("rdg_ctf_user", "ctf"),
            "RDG_CTF_PASSWORD": context.get("rdg_ctf_password", "123456"),
            "RDG_CTF_IN_ROOT_GROUP": "true"
            if context.get("rdg_ctf_in_root_group", False)
            else "false",
            "RDG_SCORING_MODE": context.get("rdg_scoring_mode", "check_service"),
            "RDG_CHECK_ENABLED": "true" if context.get("rdg_check_enabled", True) else "false",
            "RDG_CHECK_SCRIPT_PATH": context.get("rdg_check_script_path", "check/check.sh"),
            "DEFENSE_ENABLED": "true",
            "STACK_FLAG_BLOCK": flag_docker_block,
            "RDG_FLAG_DOCKER_BLOCK": flag_docker_block,
            "RDG_FLAG_START_BLOCK": flag_start_block,
            "HEALTHCHECK_BLOCK": healthcheck_block,
        }).rstrip()
        defense_start_block = render_template(defense_start_tpl, common_vars).rstrip()
    vm = context.get("vm", {}) if isinstance(context.get("vm"), dict) else {}
    common_vars = {
        "BASE_IMAGE": context["base_image"],
        "DOCKER_FROM_PLATFORM": f"--platform={context.get('docker_platform')} " if context.get("docker_platform") else "",
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
        "RDG_ENABLE_SSHD": "true" if context.get("rdg_enable_sshd") else "false",
        "RDG_SSHD_PORT": context.get("rdg_sshd_port", "22"),
        "RDG_SSHD_PASSWORD_AUTH_TEXT": "yes"
        if context.get("rdg_sshd_password_auth", True)
        else "no",
        "RDG_TTYD_BINARY_RELPATH": context.get("rdg_ttyd_binary_relpath", "ttyd"),
        "RDG_TTYD_INSTALL_FALLBACK": "true"
        if context.get("rdg_ttyd_install_fallback", True)
        else "false",
        "RDG_CTF_USER": context.get("rdg_ctf_user", "ctf"),
        "RDG_CTF_PASSWORD": context.get("rdg_ctf_password", "123456"),
        "RDG_CTF_IN_ROOT_GROUP": "true"
        if context.get("rdg_ctf_in_root_group", False)
        else "false",
        "RDG_SCORING_MODE": context.get("rdg_scoring_mode", "check_service"),
        "RDG_CHECK_ENABLED": "true" if context.get("rdg_check_enabled", True) else "false",
        "RDG_CHECK_SCRIPT_PATH": context.get("rdg_check_script_path", "check/check.sh"),
        "DEFENSE_ENABLED": "true" if context.get("defense_enabled", False) else "false",
        "STACK_FLAG_BLOCK": flag_docker_block,
        "RDG_FLAG_DOCKER_BLOCK": flag_docker_block,
        "RDG_FLAG_START_BLOCK": flag_start_block,
        "HEALTHCHECK_BLOCK": healthcheck_block,
        "DEFENSE_DOCKER_BLOCK": defense_docker_block,
        "DEFENSE_START_BLOCK": defense_start_block,
        "VM_ARCH": str(vm.get("arch", "")),
        "VM_QEMU_BINARY": str(vm.get("qemu_binary", "")),
        "VM_MACHINE": str(vm.get("machine", "")),
        "VM_ACCELERATOR": str(vm.get("accelerator", "")),
        "VM_REQUIRE_KVM": "true" if vm.get("require_kvm") else "false",
        "VM_CPU": str(vm.get("cpu", "")),
        "VM_MEMORY": str(vm.get("memory", "")),
        "VM_CPUS": str(vm.get("cpus", "")),
        "VM_KERNEL": str(vm.get("kernel", "")),
        "VM_INITRD": str(vm.get("initrd", "")),
        "VM_ROOTFS": str(vm.get("rootfs", "")),
        "VM_DRIVE_FORMAT": str(vm.get("drive_format", "")),
        "VM_APPEND": str(vm.get("append", "")),
        "VM_APPEND_QUOTED": _quote_shell(str(vm.get("append", ""))),
        "VM_NETDEV_ID": str(vm.get("netdev_id", "")),
        "VM_NET_DEVICE": str(vm.get("net_device", "")),
        "VM_NETDEV": str(vm.get("netdev", "")),
        "VM_MONITOR": str(vm.get("monitor", "")),
        "VM_EXTRA_ARGS": str(vm.get("extra_args", "")),
        "VM_ASSET_MODE": str(vm.get("asset_mode", "")),
        "VM_BUILD_SCRIPT": str(vm.get("build_script", "")),
        "VM_GUEST_FLAG_PATH": str(vm.get("guest_flag_path", "")),
        "VM_FLAG_INJECTION": str(vm.get("flag_injection", "")),
        "VM_HEALTHCHECK_MODE": str(vm.get("healthcheck_mode", "")),
        "VM_GUEST_FORWARDS": _format_vm_forwards(vm.get("guest_forwards", []))
        if isinstance(vm.get("guest_forwards"), list)
        else "",
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
        stack_id=context["stack_id"],
        flag_optional=bool(context.get("flag_optional", False)),
    )

    out_dir: Path = context["output_dir"]
    out_dir.mkdir(parents=True, exist_ok=True)

    docker_out = out_dir / "Dockerfile"
    start_out = out_dir / "start.sh"
    flag_out = out_dir / "flag"
    changeflag_out = out_dir / "changeflag.sh"

    if changeflag_out.exists():
        os.chmod(changeflag_out, 0o644)
    flag_sync_block = _render_flag_sync_block(context.get("flag_sync_paths", []))

    docker_out.write_text(rendered_docker.rstrip() + "\n", encoding="utf-8")
    start_out.write_text(rendered_start.rstrip() + "\n", encoding="utf-8")
    if context.get("stack_id") == "linux-qemu":
        vm = context.get("vm", {}) if isinstance(context.get("vm"), dict) else {}
        rootfs_path = str(vm.get("rootfs", "vm/rootfs.ext4"))
        guest_flag_path = str(vm.get("guest_flag_path", "/root/flag"))
        flag_injection = str(vm.get("flag_injection", "debugfs"))
        changeflag_out.write_text(
            "#!/bin/bash\n"
            "set -euo pipefail\n\n"
            "# linux-qemu 动态 flag 写入入口：保留外层 /flag，并按配置写入 guest rootfs。\n"
            "TARGET_PATH=\"${FLAG_PATH:-/flag}\"\n"
            "DEFAULT_FLAG=\"flag{dynamic_flag_placeholder}\"\n"
            "if [[ -n \"${FLAG:-}\" ]]; then\n"
            "  TARGET_FLAG=\"${FLAG}\"\n"
            "elif [[ -n \"${CTF_FLAG:-}\" ]]; then\n"
            "  TARGET_FLAG=\"${CTF_FLAG}\"\n"
            "elif [[ $# -gt 0 && -n \"${1:-}\" ]]; then\n"
            "  TARGET_FLAG=\"$1\"\n"
            "else\n"
            "  TARGET_FLAG=\"${DEFAULT_FLAG}\"\n"
            "fi\n"
            f"VM_ROOTFS=\"${{VM_ROOTFS:-{rootfs_path}}}\"\n"
            f"GUEST_FLAG_PATH=\"${{GUEST_FLAG_PATH:-{guest_flag_path}}}\"\n"
            f"FLAG_INJECTION=\"${{FLAG_INJECTION:-{flag_injection}}}\"\n\n"
            "if [[ -z \"${TARGET_PATH}\" ]]; then\n"
            "  echo \"[ERROR] FLAG_PATH 不能为空\" >&2\n"
            "  exit 2\n"
            "fi\n\n"
            "mkdir -p \"$(dirname \"${TARGET_PATH}\")\"\n"
            "printf '%s\\n' \"${TARGET_FLAG}\" > \"${TARGET_PATH}\"\n"
            "chmod 444 \"${TARGET_PATH}\" || true\n\n"
            f"{flag_sync_block}"
            "\n"
            "if [[ \"${FLAG_INJECTION}\" == \"none\" ]]; then\n"
            "  echo \"[INFO] flag updated at ${TARGET_PATH}; guest flag injection disabled\"\n"
            "  exit 0\n"
            "fi\n\n"
            "if [[ \"${FLAG_INJECTION}\" != \"debugfs\" ]]; then\n"
            "  echo \"[ERROR] unsupported FLAG_INJECTION=${FLAG_INJECTION}\" >&2\n"
            "  exit 2\n"
            "fi\n\n"
            "if ! command -v debugfs >/dev/null 2>&1; then\n"
            "  echo \"[ERROR] debugfs 不存在，无法写入 guest rootfs\" >&2\n"
            "  exit 2\n"
            "fi\n"
            "if [[ ! -f \"${VM_ROOTFS}\" ]]; then\n"
            "  echo \"[ERROR] VM rootfs 不存在: ${VM_ROOTFS}\" >&2\n"
            "  exit 2\n"
            "fi\n\n"
            "tmp_flag=\"$(mktemp)\"\n"
            "printf '%s\\n' \"${TARGET_FLAG}\" > \"${tmp_flag}\"\n"
            "debugfs -w -R \"rm ${GUEST_FLAG_PATH}\" \"${VM_ROOTFS}\" >/dev/null 2>&1 || true\n"
            "debugfs -w -R \"write ${tmp_flag} ${GUEST_FLAG_PATH}\" \"${VM_ROOTFS}\" >/dev/null\n"
            "debugfs -w -R \"set_inode_field ${GUEST_FLAG_PATH} mode 0100400\" \"${VM_ROOTFS}\" >/dev/null || true\n"
            "debugfs -w -R \"set_inode_field ${GUEST_FLAG_PATH} uid 0\" \"${VM_ROOTFS}\" >/dev/null || true\n"
            "debugfs -w -R \"set_inode_field ${GUEST_FLAG_PATH} gid 0\" \"${VM_ROOTFS}\" >/dev/null || true\n"
            "rm -f \"${tmp_flag}\"\n"
            "echo \"[INFO] flag updated at ${TARGET_PATH} and guest:${GUEST_FLAG_PATH}\"\n",
            encoding="utf-8",
        )
    else:
        changeflag_out.write_text(
            "#!/bin/bash\n"
            "set -euo pipefail\n\n"
            "# 平台动态 flag 写入入口。优先使用 FLAG/CTF_FLAG 环境变量，"
            "未提供时允许将第一个参数作为兜底值。\n"
            "TARGET_PATH=\"${FLAG_PATH:-/flag}\"\n"
            "DEFAULT_FLAG=\"flag{dynamic_flag_placeholder}\"\n"
            "if [[ -n \"${FLAG:-}\" ]]; then\n"
            "  TARGET_FLAG=\"${FLAG}\"\n"
            "elif [[ -n \"${CTF_FLAG:-}\" ]]; then\n"
            "  TARGET_FLAG=\"${CTF_FLAG}\"\n"
            "elif [[ $# -gt 0 && -n \"${1:-}\" ]]; then\n"
            "  TARGET_FLAG=\"$1\"\n"
            "else\n"
            "  TARGET_FLAG=\"${DEFAULT_FLAG}\"\n"
            "fi\n\n"
            "if [[ -z \"${TARGET_PATH}\" ]]; then\n"
            "  echo \"[ERROR] FLAG_PATH 不能为空\" >&2\n"
            "  exit 2\n"
            "fi\n\n"
            "mkdir -p \"$(dirname \"${TARGET_PATH}\")\"\n"
            "printf '%s\\n' \"${TARGET_FLAG}\" > \"${TARGET_PATH}\"\n"
            "chmod 444 \"${TARGET_PATH}\" || true\n"
            f"{flag_sync_block}"
            "echo \"[INFO] flag updated at ${TARGET_PATH}\"\n",
            encoding="utf-8",
        )

    os.chmod(start_out, 0o755)
    os.chmod(changeflag_out, 0o555)

    include_flag_artifact = not bool(context.get("flag_optional", False))
    if include_flag_artifact:
        flag_default = "flag{static_test_flag}\n"
        if not flag_out.exists():
            flag_out.write_text(flag_default, encoding="utf-8")
        else:
            current = flag_out.read_text(encoding="utf-8", errors="ignore")
            if not current.strip() or current.strip().lower() == "flag{}":
                os.chmod(flag_out, 0o644)
                flag_out.write_text(flag_default, encoding="utf-8")
        os.chmod(flag_out, 0o444)

    generated_check_script: str | None = None
    if context.get("rdg_check_enabled", True) and context.get("rdg_scoring_mode", "flag") == "check_service":
        check_path = _resolve_rdg_check_host_path(
            out_dir, context["workdir"], context.get("rdg_check_script_path", "check/check.sh")
        )
        if not check_path.exists():
            check_path.parent.mkdir(parents=True, exist_ok=True)
            check_path.write_text(
                "#!/bin/bash\n"
                "set -euo pipefail\n\n"
                "# CHECK_IMPLEMENT_ME: replace this scaffold with real check-service logic.\n"
                "# Contract: bash check/check.sh [target_ip] [target_port]\n"
                "# Exit code: 0=pass, 1=fail, 2=usage/runtime error.\n\n"
                "TARGET_IP=\"${1:-${TARGET_IP:-${TARGET_HOST:-127.0.0.1}}}\"\n"
                "TARGET_PORT=\"${2:-${TARGET_PORT:-80}}\"\n\n"
                "if [[ -z \"${TARGET_IP}\" || -z \"${TARGET_PORT}\" ]]; then\n"
                "  echo \"[CHECK] usage: bash check/check.sh [target_ip] [target_port]\" >&2\n"
                "  exit 2\n"
                "fi\n\n"
                "echo \"[CHECK] CHECK_IMPLEMENT_ME: add service health + exploit-negative checks\"\n"
                "echo \"[CHECK] target=${TARGET_IP}:${TARGET_PORT}\"\n"
                "exit 1\n",
                encoding="utf-8",
            )
        if check_path.is_file():
            os.chmod(check_path, 0o755)
        generated_check_script = str(check_path.relative_to(out_dir))

    generated_patch_bundle: str | None = None
    if context.get("profile") == "awdp":
        patch_root = out_dir / "patch"
        patch_src = patch_root / "src"
        patch_script = patch_root / "patch.sh"
        patch_bundle = out_dir / "patch_bundle.tar.gz"
        patch_src.mkdir(parents=True, exist_ok=True)
        readme = patch_src / "README.md"
        if not any(patch_src.iterdir()):
            readme.write_text(
                "# AWDP Patch Source\n\n"
                "将需要替换的修复文件放到本目录中，保持相对业务目录结构。\n",
                encoding="utf-8",
            )
        if not patch_script.exists():
            patch_script.write_text(
                "#!/bin/bash\n"
                "set -euo pipefail\n\n"
                "PATCH_ROOT=\"$(cd \"$(dirname \"$0\")\" && pwd)\"\n"
                "PATCH_SRC=\"${PATCH_ROOT}/src\"\n"
                "TARGET_DIR=\"${PATCH_TARGET_DIR:-" + context["workdir"] + "}\"\n\n"
                "if [[ ! -d \"${PATCH_SRC}\" ]]; then\n"
                "  echo \"[ERROR] patch/src 不存在\" >&2\n"
                "  exit 2\n"
                "fi\n\n"
                "mkdir -p \"${TARGET_DIR}\"\n"
                "cp -a \"${PATCH_SRC}/.\" \"${TARGET_DIR}/\"\n"
                "echo \"[INFO] patch files copied into ${TARGET_DIR}\"\n",
                encoding="utf-8",
            )
        os.chmod(patch_script, 0o755)
        _build_deterministic_patch_bundle(patch_bundle, patch_script, patch_src)
        generated_patch_bundle = str(patch_bundle.relative_to(out_dir))

    print("生成完成（CloverSec-CTF-Build-Dockerizer）")
    print(f"- 输出目录: {out_dir}")
    print(f"- 技术栈: {context['stack_id']} ({context['stack_display']})")
    if context["auto_detected"]:
        print(f"- 栈来源: 自动侦测（置信度 {context['confidence'] * 100:.1f}%）")
    else:
        print("- 栈来源: 显式指定（config 或 CLI）")
    print(f"- 基础镜像: {context['base_image']}")
    if context.get("runtime_supported"):
        runtime_selected = context.get("runtime_profile_selected", "")
        if runtime_selected:
            print(f"- 运行时档位: {runtime_selected}")
    print(f"- 端口: {' '.join(context['expose_ports'])}")
    print(f"- WORKDIR: {context['workdir']}")
    print(f"- 启动命令: {context['start_cmd']}")
    if context.get("healthcheck_enabled", True):
        print(
            "- HEALTHCHECK: cmd={cmd} interval={interval} timeout={timeout} retries={retries} start_period={start_period}".format(
                cmd=context.get("healthcheck_cmd", ""),
                interval=context.get("healthcheck_interval", "30s"),
                timeout=context.get("healthcheck_timeout", "5s"),
                retries=context.get("healthcheck_retries", 3),
                start_period=context.get("healthcheck_start_period", "10s"),
            )
        )
    else:
        print("- HEALTHCHECK: disabled")

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

    if context["stack_id"] in {"rdg", "secops"}:
        if include_flag_artifact:
            print("- 产物: Dockerfile, start.sh, changeflag.sh, flag, check/check.sh")
        else:
            print("- 产物: Dockerfile, start.sh, changeflag.sh, check/check.sh（flag 可选关闭）")
    else:
        print("- 产物: Dockerfile, start.sh, changeflag.sh, flag")

    if context["profile"] != "jeopardy":
        print(
            "- Defense: profile={profile}, ttyd={ttyd}, sshd={sshd}, scoring_mode={mode}, include_flag_artifact={flag}".format(
                profile=context.get("profile", "jeopardy"),
                ttyd="on" if context.get("rdg_enable_ttyd") else "off",
                sshd="on" if context.get("rdg_enable_sshd") else "off",
                mode=context.get("rdg_scoring_mode", "check_service"),
                flag="true" if context.get("rdg_include_flag_artifact", True) else "false",
            )
        )
        if generated_check_script:
            print(f"- RDG check 脚手架: {generated_check_script}")
    if generated_patch_bundle:
        print(f"- AWDP patch bundle: {generated_patch_bundle}")


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


def _challenge_path(args: argparse.Namespace) -> Path | None:
    if not args.config:
        return None
    return Path(args.config).resolve()


def _project_dir(args: argparse.Namespace) -> Path:
    return resolve_scan_dir(args.config).resolve()


def _cli_challenge(args: argparse.Namespace) -> Dict[str, Any]:
    challenge: Dict[str, Any] = {}
    if args.stack:
        challenge["stack"] = args.stack
    if args.profile:
        challenge["profile"] = args.profile
    if args.port:
        challenge["expose_ports"] = args.port
    if args.start_cmd:
        challenge["start"] = {"cmd": args.start_cmd}
    return challenge


def _accepted_path(project_dir: Path) -> Path:
    return project_dir / ".ctfbuild" / "accepted_proposal.json"


def _accepted_matches(project_dir: Path, challenge_path: Path | None) -> bool:
    if challenge_path is None or not challenge_path.exists():
        return False
    path = _accepted_path(project_dir)
    if not path.exists():
        return False
    try:
        accepted = read_json(path)
    except Exception:
        return False
    if not accepted.get("accepted"):
        return False
    return accepted.get("challenge_sha256") == sha256_file(challenge_path)


def _emit_error(args: argparse.Namespace, payload: Dict[str, Any]) -> int:
    if args.format == "json":
        print(dump_json(payload, pretty=True))
    else:
        print(f"[ERROR] {payload['code']}: {payload['summary']}", file=sys.stderr)
        if payload.get("hint"):
            print(f"[HINT] {payload['hint']}", file=sys.stderr)
    return 2


def _manual_payload(args: argparse.Namespace) -> Dict[str, Any]:
    return {
        "enabled": bool(args.manual),
        "reason": args.reason.strip() if args.manual else "",
    }


def main() -> int:
    args = parse_args()
    try:
        project_dir = _project_dir(args)
        challenge_path = _challenge_path(args)
        cli_challenge = _cli_challenge(args) if not challenge_path else {}
        audit = audit_project(
            project_dir,
            challenge_path=challenge_path if challenge_path and challenge_path.exists() else None,
            challenge=cli_challenge or None,
        )
        if args.manual and not args.reason.strip():
            return _emit_error(
                args,
                structured_error(
                    "render",
                    "RENDER_MANUAL_REASON_REQUIRED",
                    "--manual 必须同时提供 --reason。",
                    hint="示例：--manual --reason \"trusted regression example\"",
                    support_level=audit.get("support_level", "partial"),
                ),
            )
        if proposal_gate_required(audit) and not args.manual and not _accepted_matches(project_dir, challenge_path):
            return _emit_error(
                args,
                structured_error(
                    "render",
                    "CONFIG_PROPOSAL_NOT_ACCEPTED",
                    "当前输入需要先接受 proposal，render 已拒绝。",
                    file=str(challenge_path or project_dir),
                    hint="执行 workflow.py propose 与 workflow.py accept；确认无风险时可使用 --manual --reason。",
                    support_level=audit.get("support_level", "partial"),
                ),
            )

        stacks = load_stack_defs(DATA_DIR / "stacks.yaml")
        patterns = load_patterns(DATA_DIR / "patterns.yaml")
        profiles = load_profile_defs(DATA_DIR / "profiles.yaml")
        runtime_profiles = load_runtime_profiles(DATA_DIR / "runtime_profiles.yaml")
        context = build_render_context(args, stacks, patterns, profiles, runtime_profiles)
        file_plan = build_file_plan(context)
        if args.format == "json":
            with contextlib.redirect_stdout(io.StringIO()):
                render_files(context)
            print(
                dump_json(
                    structured_ok(
                        "render",
                        output_dir=str(Path(context["output_dir"])),
                        stack_id=context["stack_id"],
                        profile=context["profile"],
                        input_audit=audit,
                        manual_override=_manual_payload(args),
                        file_plan=file_plan,
                        accepted_proposal=str(_accepted_path(project_dir))
                        if _accepted_matches(project_dir, challenge_path)
                        else "",
                    ),
                    pretty=True,
                )
            )
        else:
            if args.manual:
                print(f"[WARN] manual override: {args.reason.strip()}")
            maybe_print_detect_debug(args, context["detect_details"])
            print_file_plan(file_plan)
            render_files(context)
        return 0
    except ConfigError as exc:
        return _emit_error(
            args,
            structured_error("render", "RENDER_CONFIG_ERROR", str(exc), support_level="unknown"),
        )


if __name__ == "__main__":
    sys.exit(main())
