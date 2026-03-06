#!/usr/bin/env python3
"""Validate scenario outputs and AWDP patch contract."""

from __future__ import annotations

import argparse
import subprocess
import sys
import tarfile
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
DATA_DIR = SKILL_ROOT / "data"
VALIDATE_SH = SCRIPT_DIR / "validate.sh"
RULES_FILE = DATA_DIR / "validate_scenario_rules.yaml"

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from utils import ConfigError, ensure_dict, ensure_list, load_yaml_file  # noqa: E402

ALLOWED_PROFILES = {"jeopardy", "rdg", "awd", "awdp", "secops"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate rendered scenario outputs")
    parser.add_argument("compose_file", nargs="?", help="compose file path (legacy positional)")
    parser.add_argument("root_dir", nargs="?", help="scenario output root (legacy positional)")
    parser.add_argument("--compose", help="docker-compose.yml path; default <output>/docker-compose.yml")
    parser.add_argument("--output", help="scenario output root")
    parser.add_argument("--config", help="scenario.yaml path; default <output>/scenario.yaml")
    parser.add_argument(
        "--validate-rendered",
        action="store_true",
        help="额外调用 validate.sh 校验每个渲染出的服务目录",
    )
    return parser.parse_args()


def resolve_paths(args: argparse.Namespace) -> Tuple[Path, Path, Path]:
    root = Path(args.output or args.root_dir or ".").resolve()
    compose = Path(args.compose or args.compose_file or (root / "docker-compose.yml")).resolve()
    config = Path(args.config or (root / "scenario.yaml")).resolve()
    if not compose.is_file():
        raise ConfigError(f"compose 文件不存在: {compose}")
    if not root.is_dir():
        raise ConfigError(f"output 目录不存在: {root}")
    if not config.is_file():
        raise ConfigError(f"scenario.yaml 不存在: {config}")
    return compose, root, config


def load_rules() -> Dict[str, str]:
    raw = load_yaml_file(RULES_FILE) or {}
    rules = ensure_list(raw.get("rules"), "rules")
    messages: Dict[str, str] = {}
    for item in rules:
        rule = ensure_dict(item, "rules[]")
        rule_id = str(rule.get("id") or "").strip()
        message = str(rule.get("message") or rule_id).strip()
        if rule_id:
            messages[rule_id] = message
    return messages


def rule_message(messages: Dict[str, str], rule_id: str, detail: str) -> str:
    prefix = messages.get(rule_id, rule_id)
    return f"{prefix}: {detail}"


def load_scenario(path: Path) -> Dict[str, Any]:
    raw = load_yaml_file(path) or {}
    scenario = ensure_dict(raw.get("scenario"), "scenario")
    scenario["services"] = ensure_list(scenario.get("services"), "scenario.services")
    return scenario


def load_compose(path: Path) -> Dict[str, Any]:
    raw = load_yaml_file(path) or {}
    return ensure_dict(raw, "compose")


def ensure_unique_service_names(scenario: Dict[str, Any], messages: Dict[str, str], errors: List[str]) -> Dict[str, Dict[str, Any]]:
    mapping: Dict[str, Dict[str, Any]] = {}
    for index, item in enumerate(scenario["services"], start=1):
        service = ensure_dict(item, f"scenario.services[{index}]")
        name = str(service.get("name") or "").strip()
        if not name:
            errors.append(rule_message(messages, "service-name-unique", f"scenario.services[{index}].name 不能为空"))
            continue
        if name in mapping:
            errors.append(rule_message(messages, "service-name-unique", f"重复服务名: {name}"))
            continue
        mapping[name] = service
    return mapping


def validate_service_source(service: Dict[str, Any], messages: Dict[str, str], errors: List[str]) -> None:
    project_dir = str(service.get("project_dir") or "").strip()
    challenge_path = str(service.get("challenge_path") or "").strip()
    challenge_field = service.get("challenge")
    if not challenge_path and isinstance(challenge_field, str):
        challenge_path = challenge_field.strip()
    component = str(service.get("component") or "").strip()
    variant = str(service.get("variant") or "").strip()
    has_challenge_source = bool(project_dir or challenge_path)
    has_component_source = bool(component or variant)
    if has_challenge_source == has_component_source:
        errors.append(
            rule_message(
                messages,
                "service-source-exclusive",
                f"service {service.get('name')}: 必须二选一使用 project_dir/challenge_path 或 component+variant",
            )
        )


def load_challenge_profile(challenge_path: Path) -> str:
    raw = load_yaml_file(challenge_path) or {}
    challenge = ensure_dict(raw.get("challenge"), f"challenge@{challenge_path}")
    profile = str(challenge.get("profile") or "jeopardy").strip().lower() or "jeopardy"
    if profile not in ALLOWED_PROFILES:
        raise ConfigError(f"非法 profile: {profile} @ {challenge_path}")
    return profile


def load_challenge_ports(challenge_path: Path) -> List[str]:
    raw = load_yaml_file(challenge_path) or {}
    challenge = ensure_dict(raw.get("challenge"), f"challenge@{challenge_path}")
    ports = ensure_list(challenge.get("expose_ports") or [], f"challenge.expose_ports@{challenge_path}")
    normalized: List[str] = []
    for item in ports:
        port = str(item).strip()
        if port:
            normalized.append(port)
    return normalized


def validate_host_ports(compose: Dict[str, Any], messages: Dict[str, str], errors: List[str]) -> None:
    services = ensure_dict(compose.get("services"), "compose.services")
    seen_host_ports: Set[str] = set()
    for name, item in services.items():
        service = ensure_dict(item, f"compose.services.{name}")
        ports = ensure_list(service.get("ports") or [], f"compose.services.{name}.ports")
        for mapping in ports:
            if not isinstance(mapping, str) or ":" not in mapping:
                continue
            host_port = mapping.split(":", 1)[0].strip()
            if not host_port:
                continue
            if host_port in seen_host_ports:
                errors.append(rule_message(messages, "host-port-conflict", f"端口 {host_port} 被多个服务重复使用"))
            seen_host_ports.add(host_port)


def validate_profile_alignment(
    scenario_mode: str,
    service_name: str,
    rendered_profile: str,
    messages: Dict[str, str],
    errors: List[str],
) -> None:
    if scenario_mode not in {"awd", "awdp"}:
        return
    if rendered_profile != scenario_mode:
        errors.append(
            rule_message(
                messages,
                "mode-profile-align",
                f"service {service_name} 的最终 profile={rendered_profile}，但 scenario.mode={scenario_mode}",
            )
        )


def validate_awdp_patch_contract(service_dir: Path, service_name: str, messages: Dict[str, str], errors: List[str]) -> None:
    patch_dir = service_dir / "patch"
    patch_src = patch_dir / "src"
    patch_script = patch_dir / "patch.sh"
    patch_bundle = service_dir / "patch_bundle.tar.gz"

    missing = []
    if not patch_src.is_dir():
        missing.append("patch/src")
    if not patch_script.is_file() or not patch_script.stat().st_mode & 0o111:
        missing.append("patch/patch.sh(executable)")
    if not patch_bundle.is_file():
        missing.append("patch_bundle.tar.gz")
    if missing:
        errors.append(
            rule_message(messages, "awdp-patch-required", f"service {service_name} 缺少 {', '.join(missing)}")
        )
        return

    try:
        with tarfile.open(patch_bundle, "r:gz") as tar:
            names = tar.getnames()
    except (tarfile.TarError, OSError) as exc:
        errors.append(rule_message(messages, "awdp-patch-bundle-content", f"service {service_name} 无法读取补丁包: {exc}"))
        return

    has_patch_script = "patch/patch.sh" in names
    has_patch_src = any(name == "patch/src" or name == "patch/src/" or name.startswith("patch/src/") for name in names)
    if not has_patch_script or not has_patch_src:
        missing = []
        if not has_patch_script:
            missing.append("patch/patch.sh")
        if not has_patch_src:
            missing.append("patch/src")
        errors.append(
            rule_message(messages, "awdp-patch-bundle-content", f"service {service_name} 的补丁包缺少 {', '.join(missing)}")
        )


def run_validate_sh(service_dir: Path, service_name: str, errors: List[str]) -> None:
    dockerfile = service_dir / "Dockerfile"
    start_sh = service_dir / "start.sh"
    challenge_yaml = service_dir / "challenge.yaml"
    if not dockerfile.is_file() or not start_sh.is_file() or not challenge_yaml.is_file():
        errors.append(f"service {service_name}: 缺少 Dockerfile/start.sh/challenge.yaml")
        return
    result = subprocess.run(
        ["bash", str(VALIDATE_SH), str(dockerfile), str(start_sh), str(challenge_yaml)],
        check=False,
    )
    if result.returncode != 0:
        errors.append(f"service {service_name}: validate.sh failed")


def validate_host_port_count(
    service_cfg: Dict[str, Any],
    challenge_path: Path,
    messages: Dict[str, str],
    errors: List[str],
) -> None:
    host_ports = service_cfg.get("host_ports") or []
    host_ports = ensure_list(host_ports, f"service {service_cfg.get('name')}.host_ports")
    if not host_ports:
        return
    expose_ports = load_challenge_ports(challenge_path)
    if len(host_ports) != len(expose_ports):
        errors.append(
            rule_message(
                messages,
                "host-port-count-match",
                f"service {service_cfg.get('name')} 的 host_ports 数量={len(host_ports)}，但 expose_ports 数量={len(expose_ports)}",
            )
        )


def main() -> int:
    args = parse_args()
    compose_path, output_root, scenario_path = resolve_paths(args)
    messages = load_rules()
    scenario = load_scenario(scenario_path)
    compose = load_compose(compose_path)
    errors: List[str] = []

    scenario_mode = str(scenario.get("mode") or "").strip().lower()
    if scenario_mode and scenario_mode not in ALLOWED_PROFILES:
        raise ConfigError(f"scenario.mode 不支持: {scenario_mode}")

    service_map = ensure_unique_service_names(scenario, messages, errors)
    for service in service_map.values():
        validate_service_source(service, messages, errors)

    validate_host_ports(compose, messages, errors)

    compose_services = ensure_dict(compose.get("services"), "compose.services")
    for service_name, raw in compose_services.items():
        if service_name not in service_map:
            errors.append(f"compose 中存在未在 scenario.yaml 定义的服务: {service_name}")
            continue
        service_cfg = service_map[service_name]
        service = ensure_dict(raw, f"compose.services.{service_name}")
        build = ensure_dict(service.get("build"), f"compose.services.{service_name}.build")
        context_raw = str(build.get("context") or "").strip()
        if not context_raw:
            errors.append(f"service {service_name}: 缺少 build.context")
            continue
        service_dir = (output_root / context_raw.removeprefix("./")).resolve()
        challenge_path = service_dir / "challenge.yaml"
        if not challenge_path.is_file():
            errors.append(f"service {service_name}: 缺少 challenge.yaml")
            continue

        validate_host_port_count(service_cfg, challenge_path, messages, errors)
        rendered_profile = load_challenge_profile(challenge_path)
        validate_profile_alignment(scenario_mode, service_name, rendered_profile, messages, errors)
        if rendered_profile == "awdp":
            validate_awdp_patch_contract(service_dir, service_name, messages, errors)
        if args.validate_rendered:
            run_validate_sh(service_dir, service_name, errors)

    if errors:
        for item in errors:
            print(f"[ERROR] {item}")
        return 1
    print("[OK] scenario validation passed")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ConfigError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        raise SystemExit(2)
