#!/usr/bin/env python3
"""Import docker-compose files into Scenario draft files."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
DATA_DIR = SKILL_ROOT / "data"
COMPONENTS_FILE = DATA_DIR / "components.yaml"

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from result_utils import dump_json, write_json  # noqa: E402
from utils import ConfigError, ensure_dict, ensure_list, load_yaml_file, write_unix_text  # noqa: E402

ALLOWED_MODES = {"jeopardy", "rdg", "awd", "awdp", "secops"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import docker-compose into scenario draft files")
    parser.add_argument("--compose", required=True, help="docker-compose.yml path")
    parser.add_argument("--output", required=True, help="output directory")
    parser.add_argument("--scenario-name", default="", help="scenario name")
    parser.add_argument("--mode", default="jeopardy", choices=sorted(ALLOWED_MODES), help="scenario mode")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser.parse_args()


def dump_yaml(data: Dict[str, Any], output: Path) -> None:
    try:
        import yaml
    except ModuleNotFoundError as exc:
        raise ConfigError("缺少 PyYAML，请先安装 scripts/requirements.txt") from exc
    write_unix_text(output, yaml.safe_dump(data, sort_keys=False, allow_unicode=True))


def load_compose(path: Path) -> Dict[str, Any]:
    raw = load_yaml_file(path) or {}
    compose = ensure_dict(raw, "compose")
    compose["services"] = ensure_dict(compose.get("services"), "compose.services")
    return compose


def image_aliases(image: str) -> List[str]:
    text = str(image or "").strip()
    if not text:
        return []
    no_digest = text.split("@", 1)[0]
    aliases = {text, no_digest}
    if no_digest.startswith("docker.io/library/"):
        aliases.add(no_digest.removeprefix("docker.io/library/"))
        aliases.add(no_digest.removeprefix("docker.io/"))
    elif no_digest.startswith("library/"):
        aliases.add(no_digest.removeprefix("library/"))
        aliases.add(f"docker.io/{no_digest}")
    elif "/" not in no_digest:
        aliases.add(f"library/{no_digest}")
        aliases.add(f"docker.io/library/{no_digest}")
    return sorted(item for item in aliases if item)


def component_image_map() -> Dict[str, Tuple[str, str]]:
    raw = load_yaml_file(COMPONENTS_FILE) or {}
    components = ensure_dict(raw.get("components"), "components")
    result: Dict[str, Tuple[str, str]] = {}
    for component_id, component_raw in components.items():
        component = ensure_dict(component_raw, f"components.{component_id}")
        for variant_raw in ensure_list(component.get("variants"), f"components.{component_id}.variants"):
            variant = ensure_dict(variant_raw, f"components.{component_id}.variants[]")
            image = str(variant.get("base_image") or "").strip()
            variant_id = str(variant.get("id") or "").strip()
            if image and variant_id:
                for alias in image_aliases(image):
                    result[alias] = (str(component_id), variant_id)
    return result


def resolve_component_image(image: str, image_map: Dict[str, Tuple[str, str]]) -> Tuple[str, str] | None:
    matches: List[Tuple[str, str]] = []
    for alias in image_aliases(image):
        if alias in image_map:
            matches.append(image_map[alias])
    unique = sorted(set(matches))
    if len(unique) == 1:
        return unique[0]
    return None


def normalize_environment(value: Any) -> Any:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, list):
        result: Dict[str, str] = {}
        for item in value:
            text = str(item)
            if "=" in text:
                key, val = text.split("=", 1)
                result[key] = val
            else:
                result[text] = ""
        return result
    return value


def normalize_depends_on(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, dict):
        return [str(key) for key in value.keys()]
    return [str(value)]


def normalize_ports(value: Any) -> Tuple[List[Any], List[str], List[Dict[str, str]]]:
    raw_ports = value if isinstance(value, list) else ([] if value is None else [value])
    host_ports: List[str] = []
    bindings: List[Dict[str, str]] = []
    for item in raw_ports:
        if isinstance(item, dict):
            target = item.get("target") or item.get("container_port")
            published = item.get("published") or item.get("host_port")
            protocol = str(item.get("protocol") or "tcp")
            host_ip = str(item.get("host_ip") or item.get("host_ip_address") or "")
            if target:
                binding = {"container": str(target), "protocol": protocol}
                if published:
                    binding["host"] = str(published)
                if host_ip:
                    binding["host_ip"] = host_ip
                bindings.append(binding)
            if published:
                host_ports.append(str(published))
            continue
        text = str(item).strip()
        if not text:
            continue
        protocol = "tcp"
        if "/" in text:
            text, protocol = text.split("/", 1)
        parts = text.split(":")
        if len(parts) == 1:
            bindings.append({"container": parts[0], "protocol": protocol})
        elif len(parts) == 2:
            host_ports.append(parts[0])
            bindings.append({"host": parts[0], "container": parts[1], "protocol": protocol})
        else:
            host_ports.append(parts[-2])
            bindings.append({"host_ip": ":".join(parts[:-2]), "host": parts[-2], "container": parts[-1], "protocol": protocol})
    return raw_ports, host_ports, bindings


def container_ports_from_bindings(bindings: List[Dict[str, str]]) -> List[str]:
    ports: List[str] = []
    for binding in bindings:
        protocol = str(binding.get("protocol") or "tcp")
        container = str(binding.get("container") or "").strip()
        if protocol != "tcp" or not container:
            continue
        if container.isdigit() and container not in ports:
            ports.append(container)
    return ports


def normalize_build(value: Any, compose_dir: Path) -> Tuple[Any, Path | None]:
    if value is None:
        return None, None
    if isinstance(value, str):
        return value, (compose_dir / value).resolve()
    if isinstance(value, dict):
        context = str(value.get("context") or ".").strip()
        return value, (compose_dir / context).resolve()
    return value, None


def role_for(name: str, image: str) -> str:
    haystack = f"{name} {image}".lower()
    if any(token in haystack for token in ("mysql", "mariadb", "postgres", "mongo")):
        return "db"
    if "redis" in haystack or "memcached" in haystack:
        return "cache"
    if any(token in haystack for token in ("rabbit", "mq", "kafka")):
        return "mq"
    if any(token in haystack for token in ("nginx", "apache", "httpd", "php", "tomcat", "web")):
        return "web"
    return "support"


def preserve_service_fields(service: Dict[str, Any]) -> Dict[str, Any]:
    fields = (
        "container_name",
        "command",
        "entrypoint",
        "working_dir",
        "user",
        "restart",
        "healthcheck",
        "env_file",
        "labels",
        "extra_hosts",
        "dns",
        "privileged",
        "cap_add",
        "security_opt",
    )
    return {key: service[key] for key in fields if key in service}


def finding(code: str, summary: str, level: str = "warning", hint: str = "") -> Dict[str, str]:
    item = {"code": code, "level": level, "summary": summary}
    if hint:
        item["hint"] = hint
    return item


SENSITIVE_ENV_RE = re.compile(r"(FLAG|SECRET|TOKEN|KEY|PASSWORD|PASSWD)", re.IGNORECASE)


def sensitive_env_warnings(environment: Any) -> List[Dict[str, str]]:
    if not isinstance(environment, dict):
        return []
    warnings: List[Dict[str, str]] = []
    for key in sorted(str(item) for item in environment.keys()):
        if SENSITIVE_ENV_RE.search(key):
            warnings.append(
                finding(
                    "SCENARIO_IMPORT_SENSITIVE_ENV",
                    f"environment includes sensitive-looking key: {key}",
                    hint="确认这不是动态 flag 或平台密钥后再进入最终交付。",
                )
            )
    return warnings


def service_entry(
    name: str,
    service: Dict[str, Any],
    compose_dir: Path,
    image_map: Dict[str, Tuple[str, str]],
) -> Tuple[Dict[str, Any], Dict[str, Any] | None]:
    image = str(service.get("image") or "").strip()
    build_raw, build_context = normalize_build(service.get("build"), compose_dir)
    raw_ports, host_ports, port_bindings = normalize_ports(service.get("ports"))
    volumes = service.get("volumes") if isinstance(service.get("volumes"), list) else []
    networks = service.get("networks") if service.get("networks") is not None else []
    depends_on = normalize_depends_on(service.get("depends_on"))
    environment = normalize_environment(service.get("environment"))
    preserved = preserve_service_fields(service)
    findings: List[Dict[str, str]] = []
    findings.extend(sensitive_env_warnings(environment))
    renderable: Dict[str, Any] | None = None

    if build_context is not None:
        challenge_path = build_context / "challenge.yaml"
        if challenge_path.is_file() and not volumes:
            renderable = {"name": name, "project_dir": str(build_context)}
        else:
            if not challenge_path.is_file():
                findings.append(
                    finding(
                        "SCENARIO_IMPORT_MISSING_CHALLENGE",
                        "build context has no challenge.yaml",
                        "error",
                        "先为该服务整理 challenge.yaml，或只保留在 scenario.draft.yaml 中人工迁移。",
                    )
                )
            if volumes:
                findings.append(finding("SCENARIO_IMPORT_VOLUMES_MANUAL", "compose volumes require manual migration", "error"))
    elif resolve_component_image(image, image_map):
        if volumes:
            findings.append(finding("SCENARIO_IMPORT_VOLUMES_MANUAL", "compose volumes require manual migration", "error"))
        elif preserved.get("command") is not None or preserved.get("entrypoint") is not None:
            findings.append(
                finding(
                    "SCENARIO_IMPORT_COMMAND_MANUAL",
                    "compose command/entrypoint override requires manual migration",
                    "error",
                    "官方镜像被覆盖启动命令时，不能直接按 BaseUnit 变体渲染。",
                )
            )
        else:
            component, variant = resolve_component_image(image, image_map) or ("", "")
            renderable = {"name": name, "component": component, "variant": variant}
    else:
        findings.append(
            finding(
                "SCENARIO_IMPORT_IMAGE_UNMAPPED",
                "image is not mapped to a BaseUnit component",
                "error",
                "只把官方 component 镜像或已有 challenge.yaml 的 build context 放入 renderable subset。",
            )
        )

    if renderable and host_ports:
        renderable["host_ports"] = host_ports
    if renderable:
        challenge_overrides: Dict[str, Any] = {"name": name}
        expose_ports = container_ports_from_bindings(port_bindings)
        if expose_ports:
            challenge_overrides["expose_ports"] = expose_ports
        if isinstance(environment, dict) and environment:
            challenge_overrides["extra"] = {"env": environment}
        if depends_on:
            renderable["depends_on"] = depends_on
        renderable["challenge"] = challenge_overrides

    draft = {
        "name": name,
        "role": role_for(name, image),
        "image": image,
        "build": build_raw,
        "ports": raw_ports,
        "port_bindings": port_bindings,
        "host_ports": host_ports,
        "environment": environment,
        "volumes": volumes,
        "depends_on": depends_on,
        "networks": networks,
        "preserved": preserved,
        "renderable": renderable is not None,
        "findings": findings,
        "unsupported_reasons": [item["summary"] for item in findings if item.get("level") == "error"],
    }
    if renderable:
        draft.update({key: value for key, value in renderable.items() if key not in {"challenge"}})

    return draft, renderable


def import_compose(compose_path: Path, output: Path, scenario_name: str, mode: str) -> Dict[str, Any]:
    compose = load_compose(compose_path)
    output.mkdir(parents=True, exist_ok=True)
    image_map = component_image_map()
    compose_dir = compose_path.parent
    name = scenario_name or compose_path.stem.replace("docker-compose", "scenario").strip("-_") or "scenario"

    draft_services: List[Dict[str, Any]] = []
    renderable_services: List[Dict[str, Any]] = []
    report_services: List[Dict[str, Any]] = []

    for service_name, raw_service in compose["services"].items():
        service = ensure_dict(raw_service, f"compose.services.{service_name}")
        draft, renderable = service_entry(str(service_name), service, compose_dir, image_map)
        draft_services.append(draft)
        if renderable:
            renderable_services.append(renderable)
        report_services.append(
            {
                "name": str(service_name),
                "role": draft["role"],
                "renderable": bool(renderable),
                "unsupported_reasons": draft["unsupported_reasons"],
                "findings": draft["findings"],
            }
        )

    draft_doc = {
        "scenario": {
            "name": name,
            "mode": mode,
            "draft": True,
            "imported_from": str(compose_path),
            "compose": {
                "version": compose.get("version"),
                "networks": compose.get("networks") or {},
                "volumes": compose.get("volumes") or {},
                "configs": compose.get("configs") or {},
                "secrets": compose.get("secrets") or {},
            },
            "services": draft_services,
        }
    }
    renderable_doc = {
        "scenario": {
            "name": f"{name}-renderable",
            "mode": mode,
            "services": renderable_services,
        }
    }
    report = {
        "ok": True,
        "stage": "compose_import",
        "compose_file": str(compose_path),
        "output": str(output),
        "scenario_name": name,
        "mode": mode,
        "total_services": len(draft_services),
        "renderable_services": len(renderable_services),
        "unsupported_services": len(draft_services) - len(renderable_services),
        "files": {
            "draft": str(output / "scenario.draft.yaml"),
            "renderable": str(output / "scenario.renderable.yaml"),
            "report": str(output / "import-report.json"),
        },
        "services": report_services,
        "compose": {
            "version": compose.get("version"),
            "networks": compose.get("networks") or {},
            "volumes": compose.get("volumes") or {},
            "configs": compose.get("configs") or {},
            "secrets": compose.get("secrets") or {},
        },
    }

    dump_yaml(draft_doc, output / "scenario.draft.yaml")
    dump_yaml(renderable_doc, output / "scenario.renderable.yaml")
    write_json(output / "import-report.json", report)
    return report


def main() -> int:
    args = parse_args()
    try:
        report = import_compose(Path(args.compose).resolve(), Path(args.output).resolve(), args.scenario_name, args.mode)
    except ConfigError as exc:
        payload = {
            "ok": False,
            "stage": "compose_import",
            "code": "SCENARIO_IMPORT_CONFIG_ERROR",
            "summary": str(exc),
        }
        if args.format == "json":
            print(dump_json(payload, pretty=True))
        else:
            print(f"[ERROR] {payload['code']}: {payload['summary']}", file=sys.stderr)
        return 2

    if args.format == "json":
        print(dump_json(report, pretty=True))
    else:
        print("Compose import complete")
        print(f"- services: {report['total_services']}")
        print(f"- renderable: {report['renderable_services']}")
        print(f"- unsupported: {report['unsupported_services']}")
        print(f"- output: {report['output']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
