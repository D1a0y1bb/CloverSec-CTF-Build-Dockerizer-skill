#!/usr/bin/env python3
"""Render baseunit components into platform-compatible delivery directories."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
DATA_DIR = SKILL_ROOT / "data"
RENDER_PY = SCRIPT_DIR / "render.py"

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from utils import ConfigError, ensure_dict, load_yaml_file  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render a baseunit component/variant into a delivery directory.")
    parser.add_argument("--component", help="Component family id, for example redis")
    parser.add_argument("--variant", help="Variant id, for example 7.2-alpine")
    parser.add_argument("--output", help="Output directory for rendered files")
    parser.add_argument("--name", default="", help="Optional challenge.name override")
    parser.add_argument(
        "--profile",
        default="",
        choices=["", "jeopardy", "rdg", "awd", "awdp", "secops"],
        help="Optional V2 profile override",
    )
    parser.add_argument("--pretty", action="store_true", help="Print JSON output")
    parser.add_argument("--list", action="store_true", help="List available component families and variants")
    args = parser.parse_args()

    if not args.list:
        missing = [flag for flag, value in {"--component": args.component, "--variant": args.variant, "--output": args.output}.items() if not value]
        if missing:
            parser.error("missing required arguments: " + ", ".join(missing))
    return args


def load_components() -> Dict[str, Any]:
    data = load_yaml_file(DATA_DIR / "components.yaml") or {}
    if not isinstance(data, dict):
        raise ConfigError("components.yaml top-level value must be an object")
    return ensure_dict(data.get("components"), "components")


def list_components(components: Dict[str, Any], pretty: bool) -> None:
    payload: List[Dict[str, Any]] = []
    for component_id in sorted(components):
        component = ensure_dict(components.get(component_id), f"components.{component_id}")
        variants = component.get("variants")
        if not isinstance(variants, list):
            raise ConfigError(f"components.{component_id}.variants must be a list")
        payload.append(
            {
                "component": component_id,
                "display_name": str(component.get("display_name") or component_id),
                "default_variant": str(component.get("default_variant") or ""),
                "variants": [str(item.get("id") or "") for item in variants if isinstance(item, dict)],
            }
        )

    if pretty:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    for item in payload:
        variants = ", ".join(v for v in item["variants"] if v)
        default_variant = item["default_variant"] or "-"
        print(f"{item['component']}: display_name={item['display_name']} default_variant={default_variant} variants=[{variants}]")


def resolve_variant(components: Dict[str, Any], component_id: str, variant_id: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    component = ensure_dict(components.get(component_id), f"components.{component_id}")
    variants = component.get("variants")
    if not isinstance(variants, list):
        raise ConfigError(f"components.{component_id}.variants must be a list")
    for item in variants:
        if isinstance(item, dict) and str(item.get("id") or "").strip() == variant_id:
            return component, item
    raise ConfigError(f"component={component_id} variant={variant_id} not found in components.yaml")


def build_challenge(
    component_id: str,
    variant_id: str,
    component: Dict[str, Any],
    variant: Dict[str, Any],
    profile: str,
    name_override: str,
) -> Dict[str, Any]:
    workdir = str(variant.get("workdir") or "/app").strip() or "/app"
    app_dst = str(variant.get("app_dst") or workdir).strip() or workdir
    start_cmd = str(variant.get("start_cmd") or "").strip()
    if not start_cmd:
        raise ConfigError(f"components.{component_id}.{variant_id}.start_cmd cannot be empty")

    challenge: Dict[str, Any] = {
        "challenge": {
            "name": name_override or f"baseunit-{component_id}-{variant_id}",
            "stack": "baseunit",
            "base_image": str(variant.get("base_image") or "").strip(),
            "workdir": workdir,
            "app_src": str(variant.get("app_src") or ".").strip() or ".",
            "app_dst": app_dst,
            "expose_ports": variant.get("expose_ports") or ["80"],
            "start": {
                "mode": str(variant.get("start_mode") or "cmd").strip() or "cmd",
                "cmd": start_cmd,
            },
            "runtime_deps": variant.get("runtime_deps") or [],
            "build_deps": variant.get("build_deps") or [],
            "platform": {
                "entrypoint": "/start.sh",
                "require_bash": True,
                "allow_loopback_bind": False,
            },
            "healthcheck": {
                "enabled": True,
                "cmd": str(variant.get("healthcheck_cmd") or "bash -lc 'echo > /dev/tcp/127.0.0.1/80'").strip(),
                "interval": str(variant.get("healthcheck_interval") or "30s"),
                "timeout": str(variant.get("healthcheck_timeout") or "5s"),
                "retries": int(variant.get("healthcheck_retries") or 3),
                "start_period": str(variant.get("healthcheck_start_period") or "10s"),
            },
            "extra": {
                "env": ensure_dict(variant.get("env"), f"components.{component_id}.{variant_id}.env"),
                "copy": variant.get("copy") or [],
                "user": str(variant.get("user") or ""),
            },
            "flag": {
                "path": "/flag",
                "permission": "444",
            },
        }
    }

    if profile:
        challenge["challenge"]["profile"] = profile
    notes = str(variant.get("notes") or "").strip()
    if notes:
        challenge["challenge"]["extra"]["env"]["BASEUNIT_VARIANT_NOTES"] = notes
    description = str(component.get("description") or "").strip()
    if description:
        challenge["challenge"]["extra"]["env"]["BASEUNIT_COMPONENT_DESCRIPTION"] = description
    return challenge


def render_component(args: argparse.Namespace, component: Dict[str, Any], variant: Dict[str, Any]) -> Dict[str, Any]:
    output_dir = Path(args.output).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    challenge_doc = build_challenge(
        args.component,
        args.variant,
        component,
        variant,
        args.profile.strip(),
        args.name.strip(),
    )

    try:
        import yaml
    except ModuleNotFoundError as exc:  # pragma: no cover - dependency hint
        raise ConfigError(
            "Missing PyYAML. Run: python3 -m pip install -r src/CloverSec-CTF-Build-Dockerizer/scripts/requirements.txt"
        ) from exc

    challenge_path = output_dir / "challenge.yaml"
    challenge_path.write_text(
        yaml.safe_dump(challenge_doc, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )

    cmd = [sys.executable, str(RENDER_PY), "--config", str(challenge_path), "--output", str(output_dir)]
    subprocess.run(cmd, check=True)

    payload = {
        "component": args.component,
        "variant": args.variant,
        "display_name": str(component.get("display_name") or args.component),
        "base_image": challenge_doc["challenge"]["base_image"],
        "workdir": challenge_doc["challenge"]["workdir"],
        "app_dst": challenge_doc["challenge"]["app_dst"],
        "ports": challenge_doc["challenge"]["expose_ports"],
        "start_cmd": challenge_doc["challenge"]["start"]["cmd"],
        "runtime_deps": challenge_doc["challenge"]["runtime_deps"],
        "output": str(output_dir),
    }
    notes = str(variant.get("notes") or "").strip()
    if notes:
        payload["notes"] = notes
    return payload


def main() -> int:
    args = parse_args()
    components = load_components()

    if args.list:
        list_components(components, args.pretty)
        return 0

    component, variant = resolve_variant(components, args.component.strip(), args.variant.strip())
    payload = render_component(args, component, variant)

    if args.pretty:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(
            "[OK] component={component} variant={variant} display_name={display_name} "
            "image={base_image} workdir={workdir} app_dst={app_dst} ports={ports} output={output}".format(**payload)
        )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ConfigError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        raise SystemExit(2)
