#!/usr/bin/env python3
"""Validate Bundle/Recipe rendered delivery directories."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

SCRIPT_DIR = Path(__file__).resolve().parent

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from result_utils import dump_json, structured_error, structured_ok  # noqa: E402
from utils import ConfigError, ensure_dict, ensure_list, load_yaml_file  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a rendered Bundle/Recipe directory")
    parser.add_argument("--bundle-dir", required=True, help="Rendered bundle directory")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser.parse_args()


def read_challenge(path: Path) -> Dict[str, Any]:
    raw = load_yaml_file(path) or {}
    return ensure_dict(raw.get("challenge"), "challenge")


def docker_expose_ports(dockerfile: Path) -> List[str]:
    ports: List[str] = []
    for line in dockerfile.read_text(encoding="utf-8", errors="ignore").splitlines():
        match = re.match(r"^\s*EXPOSE\s+(.+)$", line)
        if not match:
            continue
        for item in match.group(1).split():
            port = item.split("/", 1)[0].strip()
            if port:
                ports.append(port)
    return sorted(set(ports))


def validate_bundle(bundle_dir: Path) -> Dict[str, Any]:
    errors: List[str] = []
    required = ["Dockerfile", "start.sh", "changeflag.sh", "flag", "challenge.yaml"]
    for rel in required:
        if not (bundle_dir / rel).is_file():
            errors.append(f"missing {rel}")

    if errors:
        return structured_error("bundle", "BUNDLE_DELIVERY_INCOMPLETE", "; ".join(errors), support_level="partial")

    challenge = read_challenge(bundle_dir / "challenge.yaml")
    if str(challenge.get("stack") or "") != "bundle":
        errors.append("challenge.stack must be bundle")
    if str(challenge.get("profile") or "") != "jeopardy":
        errors.append("challenge.profile must be jeopardy")
    if str(challenge.get("support_level") or "") != "partial":
        errors.append("challenge.support_level must be partial")

    bundle = ensure_dict(challenge.get("bundle"), "challenge.bundle")
    recipe_id = str(bundle.get("recipe_id") or "").strip()
    if not recipe_id:
        errors.append("challenge.bundle.recipe_id is required")
    services = ensure_list(bundle.get("services"), "challenge.bundle.services")
    if not services:
        errors.append("challenge.bundle.services must not be empty")

    challenge_ports = sorted(str(port).strip() for port in ensure_list(challenge.get("expose_ports"), "challenge.expose_ports") if str(port).strip())
    exposed_ports = docker_expose_ports(bundle_dir / "Dockerfile")
    if challenge_ports != exposed_ports:
        errors.append(f"EXPOSE ports {exposed_ports} do not match challenge.expose_ports {challenge_ports}")

    if errors:
        return structured_error("bundle", "BUNDLE_CONTRACT_FAILED", "; ".join(errors), support_level="partial")

    return structured_ok(
        "bundle",
        recipe_id=recipe_id,
        bundle_dir=str(bundle_dir),
        support_level="partial",
        services=len(services),
        expose_ports=challenge_ports,
    )


def main() -> int:
    args = parse_args()
    config_error = False
    try:
        bundle_dir = Path(args.bundle_dir).resolve()
        if not bundle_dir.is_dir():
            raise ConfigError(f"bundle dir not found: {bundle_dir}")
        result = validate_bundle(bundle_dir)
    except ConfigError as exc:
        config_error = True
        result = structured_error("bundle", "BUNDLE_CONFIG_ERROR", str(exc), support_level="unknown")

    if args.format == "json":
        print(dump_json(result, pretty=True))
    elif result.get("ok"):
        print("Bundle validation passed")
        print(f"- recipe: {result['recipe_id']}")
        print(f"- services: {result['services']}")
        print(f"- expose_ports: {', '.join(result['expose_ports'])}")
    else:
        print(f"[ERROR] {result['code']}: {result['summary']}", file=sys.stderr)

    if result.get("ok"):
        return 0
    return 2 if config_error else 1


if __name__ == "__main__":
    raise SystemExit(main())
