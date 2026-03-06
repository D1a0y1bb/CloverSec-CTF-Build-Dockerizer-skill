#!/usr/bin/env python3
"""Render scenario.yaml into service directories plus docker-compose.yml."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
RENDER_PY = SCRIPT_DIR / "render.py"
RENDER_COMPONENT_PY = SCRIPT_DIR / "render_component.py"

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from utils import ConfigError, ensure_dict, ensure_list, load_yaml_file  # noqa: E402

ALLOWED_PROFILES = {"jeopardy", "rdg", "awd", "awdp", "secops"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render scenario.yaml into service dirs and docker-compose.yml")
    parser.add_argument("--config", required=True, help="scenario.yaml path")
    parser.add_argument("--output", required=True, help="output directory")
    return parser.parse_args()


def dump_yaml(data: Dict[str, Any], output: Path) -> None:
    try:
        import yaml
    except ModuleNotFoundError as exc:
        raise ConfigError("缺少 PyYAML，请先安装 requirements.txt") from exc
    output.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")


def load_scenario(path: Path) -> Dict[str, Any]:
    raw = load_yaml_file(path) or {}
    scenario = ensure_dict(raw.get("scenario"), "scenario")
    scenario["services"] = ensure_list(scenario.get("services"), "scenario.services")
    return scenario


def merge_mapping(base: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(base)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            nested = dict(merged[key])
            nested.update(value)
            merged[key] = nested
        else:
            merged[key] = value
    return merged


def ensure_unique_names(services: List[Dict[str, Any]]) -> None:
    seen = set()
    for index, item in enumerate(services, start=1):
        service = ensure_dict(item, f"scenario.services[{index}]")
        name = str(service.get("name") or "").strip()
        if not name:
            raise ConfigError(f"scenario.services[{index}].name 不能为空")
        if name in seen:
            raise ConfigError(f"service.name 重复: {name}")
        seen.add(name)


def resolve_profile(service: Dict[str, Any], scenario_mode: str, current_challenge: Dict[str, Any]) -> str:
    candidate = (
        str(service.get("profile") or "").strip().lower()
        or str(current_challenge.get("profile") or "").strip().lower()
        or scenario_mode
        or "jeopardy"
    )
    if candidate not in ALLOWED_PROFILES:
        raise ConfigError(f"service {service.get('name')}: profile 非法: {candidate}")
    return candidate


def run(cmd: List[str]) -> None:
    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def normalize_service_source(service: Dict[str, Any], scenario_dir: Path) -> Dict[str, Any]:
    project_dir_raw = str(service.get("project_dir") or "").strip()
    challenge_field = service.get("challenge")
    challenge_path_raw = str(service.get("challenge_path") or "").strip()
    if not challenge_path_raw and isinstance(challenge_field, str):
        challenge_path_raw = challenge_field.strip()

    has_challenge_source = bool(project_dir_raw or challenge_path_raw)
    has_component_source = bool(service.get("component") or service.get("variant"))
    if has_challenge_source == has_component_source:
        raise ConfigError(
            f"service {service.get('name')}: 必须二选一使用 project_dir/challenge_path 或 component+variant"
        )

    resolved: Dict[str, Any] = {"type": "challenge"}
    if has_component_source:
        component = str(service.get("component") or "").strip()
        variant = str(service.get("variant") or "").strip()
        if not component or not variant:
            raise ConfigError(f"service {service.get('name')}: component 服务必须同时提供 component 和 variant")
        return {"type": "component", "component": component, "variant": variant}

    if challenge_path_raw:
        challenge_path = (scenario_dir / challenge_path_raw).resolve()
        if not challenge_path.is_file():
            raise ConfigError(f"service {service.get('name')}: challenge_path 不存在: {challenge_path}")
        source_dir = challenge_path.parent
        resolved["challenge_path"] = challenge_path
        resolved["source_dir"] = source_dir
        return resolved

    source_dir = (scenario_dir / project_dir_raw).resolve()
    if not source_dir.is_dir():
        raise ConfigError(f"service {service.get('name')}: project_dir 不存在: {source_dir}")
    resolved["source_dir"] = source_dir
    resolved["challenge_path"] = source_dir / "challenge.yaml"
    return resolved


def load_challenge_doc(challenge_path: Path) -> Dict[str, Any]:
    if not challenge_path.exists():
        return {}
    raw = load_yaml_file(challenge_path) or {}
    return ensure_dict(raw.get("challenge"), f"challenge@{challenge_path}")


def write_challenge_doc(challenge_path: Path, challenge_doc: Dict[str, Any]) -> None:
    dump_yaml({"challenge": challenge_doc}, challenge_path)


def normalize_ports(value: Any, field_name: str) -> List[str]:
    if value is None:
        return []
    items = ensure_list(value, field_name)
    ports: List[str] = []
    for item in items:
        port = str(item).strip()
        if not port:
            continue
        if not port.isdigit() or not (1 <= int(port) <= 65535):
            raise ConfigError(f"{field_name} 端口非法: {port}")
        ports.append(port)
    return ports


def build_port_mappings(service: Dict[str, Any], challenge_doc: Dict[str, Any]) -> List[str]:
    container_ports = normalize_ports(challenge_doc.get("expose_ports"), f"service {service.get('name')} expose_ports")
    host_ports = normalize_ports(service.get("host_ports"), f"service {service.get('name')} host_ports")
    if not container_ports:
        return []
    if not host_ports:
        host_ports = list(container_ports)
    if len(host_ports) != len(container_ports):
        raise ConfigError(
            f"service {service.get('name')}: host_ports 数量({len(host_ports)}) 与 expose_ports 数量({len(container_ports)}) 不一致"
        )
    return [f"{host}:{container}" for host, container in zip(host_ports, container_ports)]


def render_from_challenge_source(
    service: Dict[str, Any],
    resolved: Dict[str, Any],
    scenario_mode: str,
    output_root: Path,
) -> Dict[str, Any]:
    name = str(service.get("name") or "").strip()
    out_dir = output_root / "services" / name
    if out_dir.exists():
        shutil.rmtree(out_dir)
    shutil.copytree(resolved["source_dir"], out_dir, dirs_exist_ok=True)

    challenge_path = out_dir / "challenge.yaml"
    base_doc = load_challenge_doc(resolved["challenge_path"])
    inline_overrides = service.get("challenge") if isinstance(service.get("challenge"), dict) else {}
    challenge_doc = merge_mapping(base_doc, inline_overrides)
    challenge_doc["name"] = name
    challenge_doc["profile"] = resolve_profile(service, scenario_mode, challenge_doc)
    write_challenge_doc(challenge_path, challenge_doc)

    run([sys.executable, str(RENDER_PY), "--config", str(challenge_path), "--output", str(out_dir)])

    rendered_doc = load_challenge_doc(challenge_path)
    port_mappings = build_port_mappings(service, rendered_doc)
    return {
        "name": name,
        "profile": str(rendered_doc.get("profile") or "jeopardy"),
        "context": f"./services/{name}",
        "dir": out_dir,
        "ports": port_mappings,
    }


def render_from_component_source(
    service: Dict[str, Any],
    resolved: Dict[str, Any],
    scenario_mode: str,
    output_root: Path,
) -> Dict[str, Any]:
    name = str(service.get("name") or "").strip()
    out_dir = output_root / "services" / name
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    initial_profile = str(service.get("profile") or scenario_mode or "").strip().lower()
    cmd = [
        sys.executable,
        str(RENDER_COMPONENT_PY),
        "--component",
        resolved["component"],
        "--variant",
        resolved["variant"],
        "--output",
        str(out_dir),
    ]
    if initial_profile:
        if initial_profile not in ALLOWED_PROFILES:
            raise ConfigError(f"service {name}: profile 非法: {initial_profile}")
        cmd.extend(["--profile", initial_profile])
    run(cmd)

    challenge_path = out_dir / "challenge.yaml"
    challenge_doc = load_challenge_doc(challenge_path)
    inline_overrides = service.get("challenge") if isinstance(service.get("challenge"), dict) else {}
    original_doc = dict(challenge_doc)
    challenge_doc = merge_mapping(challenge_doc, inline_overrides)
    challenge_doc["name"] = name
    challenge_doc["profile"] = resolve_profile(service, scenario_mode, challenge_doc)
    if challenge_doc != original_doc:
        write_challenge_doc(challenge_path, challenge_doc)
        run([sys.executable, str(RENDER_PY), "--config", str(challenge_path), "--output", str(out_dir)])
        challenge_doc = load_challenge_doc(challenge_path)

    port_mappings = build_port_mappings(service, challenge_doc)
    return {
        "name": name,
        "profile": str(challenge_doc.get("profile") or "jeopardy"),
        "context": f"./services/{name}",
        "dir": out_dir,
        "ports": port_mappings,
    }


def write_compose(output_dir: Path, scenario_name: str, services: List[Dict[str, Any]]) -> Path:
    compose = {
        "version": "3.9",
        "name": scenario_name,
        "services": {},
        "networks": {"default": {"driver": "bridge"}},
    }
    for service in services:
        compose["services"][service["name"]] = {
            "build": {"context": service["context"]},
            "ports": service["ports"],
            "networks": ["default"],
        }
    compose_path = output_dir / "docker-compose.yml"
    dump_yaml(compose, compose_path)
    return compose_path


def main() -> int:
    args = parse_args()
    scenario_path = Path(args.config).resolve()
    output_dir = Path(args.output).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    scenario = load_scenario(scenario_path)
    ensure_unique_names(scenario["services"])
    scenario_name = str(scenario.get("name") or "scenario").strip() or "scenario"
    scenario_mode = str(scenario.get("mode") or "").strip().lower()
    if scenario_mode and scenario_mode not in ALLOWED_PROFILES:
        raise ConfigError(f"scenario.mode 不支持: {scenario_mode}")

    services: List[Dict[str, Any]] = []
    for item in scenario["services"]:
        service = ensure_dict(item, "scenario.services[]")
        resolved = normalize_service_source(service, scenario_path.parent)
        if resolved["type"] == "component":
            services.append(render_from_component_source(service, resolved, scenario_mode, output_dir))
        else:
            services.append(render_from_challenge_source(service, resolved, scenario_mode, output_dir))

    shutil.copy2(scenario_path, output_dir / "scenario.yaml")
    compose_path = write_compose(output_dir, scenario_name, services)

    print(f"scenario={scenario_name}")
    print(f"mode={scenario_mode or 'none'}")
    print(f"services={len(services)}")
    print(f"compose={compose_path}")
    for service in services:
        print(
            f"- {service['name']}: profile={service['profile']} ports={' '.join(service['ports']) or '-'} dir={service['dir']}"
        )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ConfigError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        raise SystemExit(2)
