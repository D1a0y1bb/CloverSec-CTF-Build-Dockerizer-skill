#!/usr/bin/env python3
"""Import docker-compose files into Scenario draft files."""

from __future__ import annotations

import argparse
import json
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
from utils import ConfigError, ensure_dict, ensure_list, load_yaml_file  # noqa: E402

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
    output.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")


def load_compose(path: Path) -> Dict[str, Any]:
    raw = load_yaml_file(path) or {}
    compose = ensure_dict(raw, "compose")
    compose["services"] = ensure_dict(compose.get("services"), "compose.services")
    return compose


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
                result[image] = (str(component_id), variant_id)
    return result


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


def normalize_ports(value: Any) -> Tuple[List[Any], List[str]]:
    raw_ports = value if isinstance(value, list) else ([] if value is None else [value])
    host_ports: List[str] = []
    for item in raw_ports:
        if isinstance(item, dict):
            published = item.get("published") or item.get("host_port")
            if published:
                host_ports.append(str(published))
            continue
        text = str(item).strip()
        if not text:
            continue
        text = text.split("/", 1)[0]
        parts = text.split(":")
        if len(parts) == 1:
            host_ports.append(parts[0])
        elif len(parts) == 2:
            host_ports.append(parts[0])
        else:
            host_ports.append(parts[-2])
    return raw_ports, host_ports


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


def service_entry(
    name: str,
    service: Dict[str, Any],
    compose_dir: Path,
    image_map: Dict[str, Tuple[str, str]],
) -> Tuple[Dict[str, Any], Dict[str, Any] | None]:
    image = str(service.get("image") or "").strip()
    build_raw, build_context = normalize_build(service.get("build"), compose_dir)
    raw_ports, host_ports = normalize_ports(service.get("ports"))
    volumes = service.get("volumes") if isinstance(service.get("volumes"), list) else []
    networks = service.get("networks") if service.get("networks") is not None else []
    depends_on = normalize_depends_on(service.get("depends_on"))
    environment = normalize_environment(service.get("environment"))
    unsupported: List[str] = []
    renderable: Dict[str, Any] | None = None

    if build_context is not None:
        challenge_path = build_context / "challenge.yaml"
        if challenge_path.is_file() and not volumes:
            renderable = {"name": name, "project_dir": str(build_context)}
        else:
            if not challenge_path.is_file():
                unsupported.append("build context has no challenge.yaml")
            if volumes:
                unsupported.append("compose volumes require manual migration")
    elif image in image_map:
        if volumes:
            unsupported.append("compose volumes require manual migration")
        else:
            component, variant = image_map[image]
            renderable = {"name": name, "component": component, "variant": variant}
    else:
        unsupported.append("image is not mapped to a BaseUnit component")

    if renderable and host_ports:
        renderable["host_ports"] = host_ports
    if renderable:
        renderable["challenge"] = {"name": name}

    draft = {
        "name": name,
        "role": role_for(name, image),
        "image": image,
        "build": build_raw,
        "ports": raw_ports,
        "host_ports": host_ports,
        "environment": environment,
        "volumes": volumes,
        "depends_on": depends_on,
        "networks": networks,
        "renderable": renderable is not None,
        "unsupported_reasons": unsupported,
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
            }
        )

    draft_doc = {
        "scenario": {
            "name": name,
            "mode": mode,
            "draft": True,
            "imported_from": str(compose_path),
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
