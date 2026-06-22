#!/usr/bin/env python3
"""Render fixed Bundle/Recipe definitions into a platform delivery directory."""

from __future__ import annotations

import argparse
import os
import re
import shlex
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
DATA_DIR = SKILL_ROOT / "data"
RECIPES_FILE = DATA_DIR / "bundle_recipes.yaml"

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from result_utils import dump_json, structured_error, structured_ok  # noqa: E402
from utils import ConfigError, ensure_dict, ensure_list, load_yaml_file, write_unix_text  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render a fixed Bundle/Recipe delivery directory")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--recipe", help="Known recipe id")
    source.add_argument("--config", help="bundle.yaml path")
    parser.add_argument("--output", required=True, help="Output delivery directory")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser.parse_args()


def dump_yaml(data: Dict[str, Any], output: Path) -> None:
    try:
        import yaml
    except ModuleNotFoundError as exc:
        raise ConfigError("缺少 PyYAML，请先安装 scripts/requirements.txt") from exc
    write_unix_text(output, yaml.safe_dump(data, sort_keys=False, allow_unicode=True))


def load_recipes() -> Dict[str, Dict[str, Any]]:
    raw = load_yaml_file(RECIPES_FILE) or {}
    recipes = ensure_list(raw.get("recipes"), "recipes")
    result: Dict[str, Dict[str, Any]] = {}
    for item in recipes:
        recipe = ensure_dict(item, "recipes[]")
        recipe_id = str(recipe.get("id") or "").strip()
        if not recipe_id:
            raise ConfigError("bundle recipe 缺少 id")
        result[recipe_id] = recipe
    return result


def service_signature(services: List[Dict[str, Any]]) -> List[Tuple[str, str]]:
    signature = []
    for service in services:
        service_id = str(service.get("id") or "").strip().lower()
        version = str(service.get("version") or "").strip()
        if service_id:
            signature.append((service_id, version))
    return sorted(signature)


def slugify_identifier(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_.-]+", "-", value.strip().lower()).strip("-")
    return slug or "custom-bundle"


def normalize_start_commands(raw: Any, field: str) -> List[Dict[str, str]]:
    items = ensure_list(raw, field)
    if not items:
        raise ConfigError("BUNDLE_UNSUPPORTED_COMBINATION: custom bundle requires start_commands")

    commands: List[Dict[str, str]] = []
    total = len(items)
    for idx, item in enumerate(items):
        if isinstance(item, str):
            cmd = item.strip()
            mode = "foreground" if idx == total - 1 else "background"
        else:
            entry = ensure_dict(item, f"{field}[]")
            cmd = str(entry.get("cmd") or entry.get("command") or "").strip()
            mode = str(entry.get("mode") or ("foreground" if idx == total - 1 else "background")).strip()
        if not cmd:
            raise ConfigError(f"{field}[{idx}] 缺少 cmd")
        if mode not in {"background", "foreground", "wait"}:
            raise ConfigError(f"{field}[{idx}].mode 仅支持 background/foreground/wait")
        if mode in {"foreground", "wait"} and idx != total - 1:
            raise ConfigError(f"{field}[{idx}].mode={mode} 必须是最后一个启动步骤")
        commands.append({"cmd": cmd, "mode": mode})
    return commands


def can_build_custom_recipe(bundle: Dict[str, Any]) -> bool:
    explicit = str(bundle.get("recipe") or bundle.get("recipe_id") or "").strip().lower()
    if explicit in {"custom", "custom-explicit"} or bundle.get("custom") is True:
        return True
    return bool(bundle.get("base_image") and bundle.get("start_commands") and bundle.get("services") and bundle.get("expose_ports"))


def custom_recipe_from_bundle(bundle: Dict[str, Any], explicit_recipe_id: str = "") -> Dict[str, Any]:
    name = str(bundle.get("name") or explicit_recipe_id or "custom-bundle").strip()
    recipe_id_raw = explicit_recipe_id.strip()
    if recipe_id_raw in {"", "custom", "custom-explicit"}:
        recipe_id = f"custom-{slugify_identifier(name)}"
    else:
        recipe_id = slugify_identifier(recipe_id_raw)

    base_image = str(bundle.get("base_image") or "").strip()
    if not base_image:
        raise ConfigError("BUNDLE_UNSUPPORTED_COMBINATION: custom bundle requires base_image")

    expose_ports = [str(port).strip() for port in ensure_list(bundle.get("expose_ports"), "bundle.expose_ports") if str(port).strip()]
    if not expose_ports:
        raise ConfigError("BUNDLE_UNSUPPORTED_COMBINATION: custom bundle requires expose_ports")

    services = [ensure_dict(item, "bundle.services[]") for item in ensure_list(bundle.get("services"), "bundle.services")]
    if not services:
        raise ConfigError("BUNDLE_UNSUPPORTED_COMBINATION: custom bundle requires services")

    start_commands = normalize_start_commands(bundle.get("start_commands"), "bundle.start_commands")
    install_commands = [str(item).strip() for item in ensure_list(bundle.get("install_commands", []), "bundle.install_commands") if str(item).strip()]
    workdir = str(bundle.get("workdir") or "/opt/bundle/app").strip()
    app_dst = str(bundle.get("app_dst") or workdir).strip()
    healthcheck_cmd = str(bundle.get("healthcheck_cmd") or f"bash -lc 'echo > /dev/tcp/127.0.0.1/{expose_ports[0]}'").strip()
    startup_order = ensure_list(bundle.get("startup_order", [str(item.get("id") or "").strip() for item in services if str(item.get("id") or "").strip()]), "bundle.startup_order")
    notes = [str(item) for item in ensure_list(bundle.get("notes", []), "bundle.notes")]
    notes.insert(0, "Custom bundle uses user-supplied install_commands and start_commands; no automatic version solver is used.")

    return {
        "id": recipe_id,
        "display_name": name,
        "support_level": str(bundle.get("support_level") or "partial"),
        "base_os": str(bundle.get("base_os") or base_image),
        "base_image": base_image,
        "mode": str(bundle.get("mode") or "single_container"),
        "workdir": workdir,
        "app_dst": app_dst,
        "expose_ports": expose_ports,
        "healthcheck_cmd": healthcheck_cmd,
        "install_commands": install_commands,
        "start_commands": start_commands,
        "services": services,
        "startup_order": startup_order,
        "notes": notes,
        "custom": True,
    }


def match_recipe(bundle: Dict[str, Any], recipes: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    explicit = str(bundle.get("recipe") or bundle.get("recipe_id") or "").strip()
    if explicit:
        if explicit not in recipes:
            if can_build_custom_recipe(bundle):
                return custom_recipe_from_bundle(bundle, explicit)
            raise ConfigError(f"BUNDLE_UNSUPPORTED_COMBINATION: unknown recipe {explicit}")
        return recipes[explicit]

    requested_services = [ensure_dict(item, "bundle.services[]") for item in ensure_list(bundle.get("services"), "bundle.services")]
    requested_signature = service_signature(requested_services)
    requested_base = str(bundle.get("base_os") or bundle.get("base_image") or "").strip()
    requested_mode = str(bundle.get("mode") or "single_container").strip()

    for recipe in recipes.values():
        if requested_base and requested_base != str(recipe.get("base_os") or recipe.get("base_image") or "").strip():
            continue
        if requested_mode != str(recipe.get("mode") or "single_container").strip():
            continue
        if requested_signature == service_signature(ensure_list(recipe.get("services"), "recipe.services")):
            return recipe

    if can_build_custom_recipe(bundle):
        return custom_recipe_from_bundle(bundle)

    raise ConfigError("BUNDLE_UNSUPPORTED_COMBINATION: no fixed recipe matches requested services")


def load_bundle_request(config_path: Path | None, recipe_id: str | None, recipes: Dict[str, Dict[str, Any]]) -> Tuple[Dict[str, Any], Dict[str, Any], Path | None]:
    if recipe_id:
        if recipe_id not in recipes:
            raise ConfigError(f"BUNDLE_UNSUPPORTED_COMBINATION: unknown recipe {recipe_id}")
        return {"name": recipe_id, "recipe": recipe_id}, recipes[recipe_id], None

    assert config_path is not None
    raw = load_yaml_file(config_path) or {}
    if not isinstance(raw, dict):
        raise ConfigError("bundle.yaml 顶层必须是对象")
    bundle = ensure_dict(raw.get("bundle"), "bundle")
    recipe = match_recipe(bundle, recipes)
    return bundle, recipe, config_path.parent


def copy_app(bundle: Dict[str, Any], config_dir: Path | None, output: Path, recipe: Dict[str, Any]) -> None:
    app_dir = output / "app"
    if app_dir.exists():
        shutil.rmtree(app_dir)
    app_dir.mkdir(parents=True, exist_ok=True)

    app_src_raw = str(bundle.get("app_src") or "").strip()
    if app_src_raw and config_dir:
        src = (config_dir / app_src_raw).resolve()
        if src.is_dir():
            shutil.copytree(src, app_dir, dirs_exist_ok=True)
            return
        if src.is_file():
            shutil.copy2(src, app_dir / src.name)
            return
        raise ConfigError(f"bundle.app_src 不存在: {src}")

    if recipe.get("custom"):
        write_unix_text(
            app_dir / "index.html",
            f"bundle custom {recipe.get('id')}\n",
        )
    elif str(recipe.get("id")) == "tomcat85-jdk8-mysql57":
        write_unix_text(
            app_dir / "index.jsp",
            "<% out.println(\"bundle tomcat85-jdk8-mysql57\"); %>\n",
        )
    else:
        write_unix_text(app_dir / "index.html", "bundle legacy-centos7-python39-mysql57-redis5\n")


def dockerfile_text(recipe: Dict[str, Any]) -> str:
    install_commands = ensure_list(recipe.get("install_commands"), "recipe.install_commands")
    run_lines = " && \\\n    ".join(str(item) for item in install_commands) or ":"
    expose_ports = " ".join(str(port) for port in ensure_list(recipe.get("expose_ports"), "recipe.expose_ports"))
    healthcheck_cmd = str(recipe.get("healthcheck_cmd") or "bash -lc 'true'")
    app_dst = str(recipe.get("app_dst") or recipe.get("workdir") or "/app")
    return (
        f"FROM {recipe['base_image']}\n\n"
        "ENV DEBIAN_FRONTEND=noninteractive\n\n"
        f"RUN set -eux; \\\n    {run_lines}\n\n"
        f"WORKDIR {recipe['workdir']}\n\n"
        f"COPY app {app_dst}\n"
        "COPY flag /flag\n"
        "COPY changeflag.sh /changeflag.sh\n"
        "COPY start.sh /start.sh\n\n"
        "RUN chmod 555 /start.sh /changeflag.sh && chmod 444 /flag\n\n"
        f"EXPOSE {expose_ports}\n\n"
        f"HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=20s CMD {healthcheck_cmd}\n\n"
        "ENTRYPOINT [\"/start.sh\"]\n"
    )


def start_script_text(recipe: Dict[str, Any]) -> str:
    recipe_id = str(recipe.get("id"))
    if recipe.get("custom"):
        lines = [
            "#!/bin/bash",
            "set -euo pipefail",
            "",
            f"cd {shlex.quote(str(recipe.get('workdir') or '/opt/bundle/app'))}",
            f"echo \"[INFO] starting bundle recipe: {recipe_id}\"",
            "",
        ]
        for item in normalize_start_commands(recipe.get("start_commands"), "recipe.start_commands"):
            quoted = shlex.quote(item["cmd"])
            mode = item["mode"]
            if mode == "background":
                lines.append(f"bash -lc {quoted} &")
            elif mode == "foreground":
                lines.append(f"exec bash -lc {quoted}")
            elif mode == "wait":
                lines.append("wait -n || exit 1")
        if not any(item["mode"] in {"foreground", "wait"} for item in normalize_start_commands(recipe.get("start_commands"), "recipe.start_commands")):
            lines.append("wait -n || exit 1")
        return "\n".join(lines) + "\n"

    if recipe_id == "legacy-centos7-python39-mysql57-redis5":
        return """#!/bin/bash
set -euo pipefail

cd /opt/bundle/app
echo "[INFO] starting bundle recipe: legacy-centos7-python39-mysql57-redis5"

if command -v mysqld_safe >/dev/null 2>&1; then
  mysqld_safe --datadir=/var/lib/mysql --bind-address=0.0.0.0 >/tmp/bundle-mysql.log 2>&1 &
else
  echo "[WARN] mysql 5.7 runtime not installed; static recipe validation only"
fi

if command -v redis-server >/dev/null 2>&1; then
  redis-server --protected-mode no --bind 0.0.0.0 >/tmp/bundle-redis.log 2>&1 &
else
  echo "[WARN] redis 5 runtime not installed; static recipe validation only"
fi

if command -v python3.9 >/dev/null 2>&1; then
  exec python3.9 -m http.server 8000 --bind 0.0.0.0
elif command -v python3 >/dev/null 2>&1; then
  exec python3 -m http.server 8000 --bind 0.0.0.0
fi

echo "[WARN] python runtime not installed; waiting for any background service"
wait -n || exit 1
"""
    if recipe_id == "tomcat85-jdk8-mysql57":
        return """#!/bin/bash
set -euo pipefail

cd /usr/local/tomcat
echo "[INFO] starting bundle recipe: tomcat85-jdk8-mysql57"

if command -v mysqld_safe >/dev/null 2>&1; then
  mysqld_safe --datadir=/var/lib/mysql --bind-address=0.0.0.0 >/tmp/bundle-mysql.log 2>&1 &
else
  echo "[WARN] mysql 5.7 runtime not installed; static recipe validation only"
fi

if command -v catalina.sh >/dev/null 2>&1; then
  exec catalina.sh run
fi

echo "[ERROR] catalina.sh not found"
exit 1
"""
    raise ConfigError(f"BUNDLE_UNSUPPORTED_COMBINATION: no start template for {recipe_id}")


def changeflag_text() -> str:
    return """#!/bin/bash
set -euo pipefail

TARGET_PATH="${FLAG_PATH:-/flag}"
DEFAULT_FLAG="flag{bundle_recipe_placeholder}"
if [[ -n "${FLAG:-}" ]]; then
  TARGET_FLAG="${FLAG}"
elif [[ -n "${CTF_FLAG:-}" ]]; then
  TARGET_FLAG="${CTF_FLAG}"
elif [[ $# -gt 0 && -n "${1:-}" ]]; then
  TARGET_FLAG="$1"
else
  TARGET_FLAG="${DEFAULT_FLAG}"
fi

mkdir -p "$(dirname "${TARGET_PATH}")"
printf '%s\\n' "${TARGET_FLAG}" > "${TARGET_PATH}"
chmod 444 "${TARGET_PATH}"
chown root:root "${TARGET_PATH}" 2>/dev/null || true
echo "[INFO] flag updated"
"""


def challenge_doc(bundle: Dict[str, Any], recipe: Dict[str, Any]) -> Dict[str, Any]:
    name = str(bundle.get("name") or recipe.get("id")).strip()
    return {
        "challenge": {
            "name": name,
            "stack": "bundle",
            "profile": "jeopardy",
            "support_level": str(recipe.get("support_level") or "partial"),
            "base_image": str(recipe["base_image"]),
            "workdir": str(recipe["workdir"]),
            "app_src": "app",
            "app_dst": str(recipe.get("app_dst") or recipe["workdir"]),
            "expose_ports": [str(port) for port in ensure_list(recipe.get("expose_ports"), "recipe.expose_ports")],
            "start": {"mode": "cmd", "cmd": "bash /start.sh"},
            "healthcheck": {
                "enabled": True,
                "cmd": str(recipe.get("healthcheck_cmd") or "bash -lc 'true'"),
            },
            "bundle": {
                "recipe_id": str(recipe["id"]),
                "mode": str(recipe.get("mode") or "single_container"),
                "support_level": str(recipe.get("support_level") or "partial"),
                "services": ensure_list(recipe.get("services"), "recipe.services"),
                "startup_order": ensure_list(recipe.get("startup_order"), "recipe.startup_order"),
                "notes": ensure_list(recipe.get("notes"), "recipe.notes"),
            },
        }
    }


def render_bundle(bundle: Dict[str, Any], recipe: Dict[str, Any], config_dir: Path | None, output: Path) -> Dict[str, Any]:
    planned = ["Dockerfile", "start.sh", "changeflag.sh", "flag", "challenge.yaml", "app/"]
    file_plan = [
        {
            "path": item,
            "action": "overwrite" if item not in {"app/"} else "copy_or_create",
            "exists": (output / item.rstrip("/")).exists(),
        }
        for item in planned
    ]
    output.mkdir(parents=True, exist_ok=True)
    copy_app(bundle, config_dir, output, recipe)
    write_unix_text(output / "Dockerfile", dockerfile_text(recipe))
    write_unix_text(output / "start.sh", start_script_text(recipe))
    write_unix_text(output / "changeflag.sh", changeflag_text())
    write_unix_text(output / "flag", "flag{bundle_recipe_placeholder}\n")
    dump_yaml(challenge_doc(bundle, recipe), output / "challenge.yaml")
    os.chmod(output / "start.sh", 0o755)
    os.chmod(output / "changeflag.sh", 0o755)
    os.chmod(output / "flag", 0o444)
    return structured_ok(
        "bundle",
        recipe_id=str(recipe["id"]),
        output=str(output),
        support_level=str(recipe.get("support_level") or "partial"),
        files=["Dockerfile", "start.sh", "changeflag.sh", "flag", "challenge.yaml"],
        file_plan=file_plan,
    )


def main() -> int:
    args = parse_args()
    try:
        recipes = load_recipes()
        bundle, recipe, config_dir = load_bundle_request(
            Path(args.config).resolve() if args.config else None,
            args.recipe,
            recipes,
        )
        result = render_bundle(bundle, recipe, config_dir, Path(args.output).resolve())
    except ConfigError as exc:
        result = structured_error(
            "bundle",
            "BUNDLE_UNSUPPORTED_COMBINATION" if "BUNDLE_UNSUPPORTED_COMBINATION" in str(exc) else "BUNDLE_CONFIG_ERROR",
            str(exc),
            support_level="unsupported",
        )
        if args.format == "json":
            print(dump_json(result, pretty=True))
        else:
            print(f"[ERROR] {result['code']}: {result['summary']}", file=sys.stderr)
        return 2

    if args.format == "json":
        print(dump_json(result, pretty=True))
    else:
        print("Bundle render complete")
        print(f"- recipe: {result['recipe_id']}")
        print(f"- output: {result['output']}")
        print(f"- support_level: {result['support_level']}")
        print("- file_plan:")
        for item in result.get("file_plan", []):
            exists = "exists" if item.get("exists") else "new"
            print(f"  - {item['path']}: {item['action']} ({exists})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
