#!/usr/bin/env python3
"""Extract normalized V2 validation context from challenge.yaml."""

from __future__ import annotations

import shlex
import sys
from pathlib import Path

try:
    import yaml
except ModuleNotFoundError:
    raise SystemExit(0)


def pick_bool(source: dict, name: str, default: bool) -> str:
    value = source.get(name, default)
    if isinstance(value, str):
        value = value.strip().lower() in {"true", "1", "yes", "y"}
    return "true" if bool(value) else "false"


def main() -> int:
    if len(sys.argv) < 2:
        return 0

    path = Path(sys.argv[1])
    if not path.is_file():
        return 0

    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    challenge = raw.get("challenge") or {}
    if not isinstance(challenge, dict):
        return 0

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
        "ALLOW_LOOPBACK_BIND_CFG": (
            "true"
            if bool((challenge.get("platform") or {}).get("allow_loopback_bind", False))
            else "false"
        ),
        "FLAG_OPTIONAL_CFG": flag_optional,
        "START_CMD_CFG": str(((challenge.get("start") or {}).get("cmd")) or "").strip(),
    }

    for key, value in items.items():
        print(f"{key}={shlex.quote(value)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
