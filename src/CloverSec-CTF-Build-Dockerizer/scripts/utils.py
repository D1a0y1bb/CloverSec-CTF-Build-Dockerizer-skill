#!/usr/bin/env python3
"""CloverSec-CTF-Build-Dockerizer 脚本公共函数。"""

from __future__ import annotations

import re
import shlex
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


_VAR_PATTERN = re.compile(r"\{\{([A-Z0-9_]+)\}\}")
_INCLUDE_PATTERN = re.compile(r"\{\{\>\s*([^}]+?)\s*\}\}")
_ENV_KEY_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class ConfigError(Exception):
    """用户输入或模板渲染相关错误。"""


def load_yaml_file(path: Path) -> Any:
    """加载 YAML；若缺少 PyYAML，抛出带安装提示的异常。"""
    try:
        import yaml
    except ModuleNotFoundError as exc:
        raise ConfigError(
            "缺少依赖 PyYAML。请先执行："
            "python3 -m pip install -r src/CloverSec-CTF-Build-Dockerizer/scripts/requirements.txt"
        ) from exc

    if not path.exists():
        raise ConfigError(f"YAML 文件不存在: {path}")

    try:
        with path.open("r", encoding="utf-8") as fh:
            return yaml.safe_load(fh)
    except Exception as exc:  # pragma: no cover - 具体异常由 yaml 决定
        raise ConfigError(f"YAML 解析失败: {path}\n{exc}") from exc


def ensure_dict(value: Any, field_name: str) -> Dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ConfigError(f"字段 {field_name} 必须是对象")
    return value


def ensure_list(value: Any, field_name: str) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    raise ConfigError(f"字段 {field_name} 必须是数组")


def first_non_empty(*values: Any) -> Any:
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and value.strip() == "":
            continue
        return value
    return None


def normalize_ports(value: Any) -> List[str]:
    """将端口输入统一为字符串列表。"""
    if value is None:
        return []

    if isinstance(value, (int, float)):
        return [str(int(value))]

    if isinstance(value, str):
        raw = value.replace(",", " ").split()
        return [item.strip() for item in raw if item.strip()]

    if isinstance(value, list):
        ports: List[str] = []
        for item in value:
            if isinstance(item, (int, float)):
                ports.append(str(int(item)))
            elif isinstance(item, str):
                item = item.strip()
                if item:
                    ports.append(item)
            else:
                raise ConfigError("expose_ports 仅支持字符串或数字")
        return ports

    raise ConfigError("expose_ports 字段格式不正确")


def _resolve_include_path(include_ref: str, template_dir: Path, templates_root: Path) -> Path:
    include_ref = include_ref.strip()
    if not include_ref:
        raise ConfigError("include 路径不能为空")

    candidates = []

    include_path = Path(include_ref)
    if include_path.is_absolute():
        candidates.append(include_path)
    else:
        candidates.append((template_dir / include_ref).resolve())
        candidates.append((templates_root / include_ref).resolve())

    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate

    raise ConfigError(
        f"模板 include 文件不存在: {include_ref}（已尝试: {', '.join(str(c) for c in candidates)}）"
    )


def resolve_template_includes(
    template_text: str,
    template_dir: Path,
    templates_root: Path,
    visiting: Optional[Set[Path]] = None,
) -> str:
    visiting = visiting or set()

    def _is_inline_include(match: re.Match[str]) -> bool:
        """判断 include 是否与同一行其他内容拼接（例如 `{{> x }}; \\`）。"""
        start = match.start()
        end = match.end()

        line_start = template_text.rfind("\n", 0, start) + 1
        line_end = template_text.find("\n", end)
        if line_end < 0:
            line_end = len(template_text)

        prefix = template_text[line_start:start]
        suffix = template_text[end:line_end]
        return bool(prefix.strip() or suffix.strip())

    def _replace(match: re.Match[str]) -> str:
        include_ref = match.group(1).strip()
        include_path = _resolve_include_path(include_ref, template_dir, templates_root)

        include_real = include_path.resolve()
        if include_real in visiting:
            chain = " -> ".join(str(p) for p in [*visiting, include_real])
            raise ConfigError(f"检测到循环 include: {chain}")

        include_raw = include_path.read_text(encoding="utf-8")
        next_visiting = set(visiting)
        next_visiting.add(include_real)
        resolved = resolve_template_includes(
            include_raw, include_path.parent, templates_root, next_visiting
        )

        # inline include 会直接拼接在当前行，去掉结尾换行避免渲染出独立 `;` 行。
        if _is_inline_include(match):
            resolved = resolved.rstrip("\r\n")
        return resolved

    return _INCLUDE_PATTERN.sub(_replace, template_text)


def load_template_with_includes(template_path: Path, templates_root: Path) -> str:
    if not template_path.exists():
        raise ConfigError(f"模板文件不存在: {template_path}")

    raw = template_path.read_text(encoding="utf-8")
    return resolve_template_includes(raw, template_path.parent, templates_root, {template_path.resolve()})


def render_template(template_text: str, variables: Dict[str, str]) -> str:
    rendered = template_text
    for key, value in variables.items():
        rendered = rendered.replace("{{" + key + "}}", value)

    leftovers = sorted(set(_VAR_PATTERN.findall(rendered)))
    if leftovers:
        raise ConfigError(f"模板渲染后仍存在未替换变量: {', '.join(leftovers)}")

    return rendered


def build_runtime_deps_install(runtime_deps: List[str], base_image: str) -> str:
    deps = [dep.strip() for dep in runtime_deps if isinstance(dep, str) and dep.strip()]
    if not deps:
        return ":"

    dep_expr = " ".join(shlex.quote(dep) for dep in deps)
    lower_image = base_image.lower()

    if "alpine" in lower_image:
        return f"apk add --no-cache {dep_expr}"

    return (
        "apt-get update && "
        f"apt-get install -y --no-install-recommends {dep_expr} && "
        "rm -rf /var/lib/apt/lists/*"
    )


def build_npm_install_block(custom_block: str = "") -> str:
    block = custom_block.strip()
    if block:
        return block

    return (
        "RUN set -eux; \\\n"
        "    if [ -f package-lock.json ] || [ -f npm-shrinkwrap.json ]; then \\\n"
        "      npm ci --omit=dev || npm ci; \\\n"
        "      npm cache clean --force || true; \\\n"
        "    elif [ -f package.json ]; then \\\n"
        "      npm install --omit=dev || npm install; \\\n"
        "      npm cache clean --force || true; \\\n"
        "    else \\\n"
        "      echo \"[INFO] 未检测到 package.json，跳过 npm 安装\"; \\\n"
        "    fi"
    )


def build_pip_requirements_block(custom_block: str = "") -> str:
    block = custom_block.strip()
    if block:
        return block

    return (
        "RUN set -eux; \\\n"
        "    if [ -f requirements.txt ]; then \\\n"
        "      pip install --no-cache-dir -r requirements.txt; \\\n"
        "    else \\\n"
        "      echo \"[INFO] 未检测到 requirements.txt，跳过 pip 安装\"; \\\n"
        "    fi"
    )


def build_copy_app(copy_items: List[Dict[str, Any]]) -> str:
    if not copy_items:
        return "# no extra copy"

    lines: List[str] = []
    for idx, item in enumerate(copy_items, start=1):
        if not isinstance(item, dict):
            raise ConfigError(f"extra.copy 第 {idx} 项必须是对象")

        src = item.get("from", "")
        dst = item.get("to", "")
        if not src or not dst:
            raise ConfigError(f"extra.copy 第 {idx} 项必须同时包含 from/to")

        lines.append(f"COPY {src} {dst}")

    return "\n".join(lines)


def build_env_exports(env_map: Dict[str, Any]) -> str:
    if not env_map:
        return ":"

    lines: List[str] = []
    for key, value in env_map.items():
        if not _ENV_KEY_PATTERN.match(str(key)):
            raise ConfigError(f"非法环境变量名: {key}")
        lines.append(f"export {key}={shlex.quote(str(value))}")

    return "\n".join(lines)


def build_docker_env_lines(env_map: Dict[str, Any]) -> str:
    if not env_map:
        return "# no docker env"

    lines: List[str] = []
    for key, value in env_map.items():
        if not _ENV_KEY_PATTERN.match(str(key)):
            raise ConfigError(f"非法环境变量名: {key}")

        escaped = str(value).replace("\\", "\\\\").replace('"', '\\"')
        lines.append(f'ENV {key}="{escaped}"')

    return "\n".join(lines)


def load_stack_defs(stacks_yaml_path: Path) -> Dict[str, Dict[str, Any]]:
    data = load_yaml_file(stacks_yaml_path)
    if not isinstance(data, dict):
        raise ConfigError(f"栈定义文件格式错误: {stacks_yaml_path}")

    stacks_raw = data.get("stacks")
    if not isinstance(stacks_raw, list) or not stacks_raw:
        raise ConfigError("stacks.yaml 中 stacks 必须是非空数组")

    stacks: Dict[str, Dict[str, Any]] = {}
    for item in stacks_raw:
        if not isinstance(item, dict):
            raise ConfigError("stacks.yaml 中每个栈定义必须是对象")
        stack_id = item.get("id")
        if not isinstance(stack_id, str) or not stack_id.strip():
            raise ConfigError("stacks.yaml 栈定义缺少有效 id")
        stacks[stack_id] = item

    return stacks


def load_patterns(patterns_yaml_path: Path) -> Dict[str, Any]:
    data = load_yaml_file(patterns_yaml_path)
    if data is None:
        return {"stacks": {}}
    if not isinstance(data, dict):
        raise ConfigError(f"patterns.yaml 格式错误: {patterns_yaml_path}")

    stacks = data.get("stacks", {})
    if not isinstance(stacks, dict):
        raise ConfigError("patterns.yaml 中 stacks 必须是对象")

    return data


def _first_existing_file(scan_dir: Path, files: List[str]) -> Optional[str]:
    for item in files:
        if (scan_dir / item).is_file():
            return item
    return None


def _any_glob(scan_dir: Path, globs: List[str]) -> Optional[str]:
    for pattern in globs:
        matched = sorted(scan_dir.glob(pattern))
        if matched:
            try:
                return str(matched[0].relative_to(scan_dir))
            except ValueError:
                return str(matched[0])
    return None


def _rule_matches(scan_dir: Path, rule: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    files = [str(x) for x in ensure_list(rule.get("any_of_files"), "patterns.rules.any_of_files")]
    dirs = [str(x) for x in ensure_list(rule.get("any_of_dirs"), "patterns.rules.any_of_dirs")]
    globs = [str(x) for x in ensure_list(rule.get("any_of_globs"), "patterns.rules.any_of_globs")]

    if not files and not dirs and not globs:
        # 无条件规则
        return True, None

    file_hit = _first_existing_file(scan_dir, files)
    if file_hit:
        return True, file_hit

    for item in dirs:
        if (scan_dir / item).is_dir():
            return True, item

    glob_hit = _any_glob(scan_dir, globs)
    if glob_hit:
        return True, glob_hit

    return False, None


def _format_start_cmd(template: str, entry_file: Optional[str]) -> str:
    if "{entry_file}" in template:
        if not entry_file:
            return ""
        return template.replace("{entry_file}", entry_file)
    return template


def infer_from_patterns(scan_dir: Path, stack_id: str, patterns_data: Dict[str, Any]) -> Dict[str, Any]:
    stacks = ensure_dict(patterns_data.get("stacks"), "patterns.stacks")
    stack_patterns = ensure_dict(stacks.get(stack_id), f"patterns.stacks.{stack_id}")

    defaults = ensure_dict(stack_patterns.get("defaults"), f"patterns.{stack_id}.defaults")
    rules = ensure_list(stack_patterns.get("rules"), f"patterns.{stack_id}.rules")
    entry_files = [str(x) for x in ensure_list(stack_patterns.get("entry_files"), f"patterns.{stack_id}.entry_files")]

    inferred_start: Optional[str] = None
    inferred_ports: List[str] = []
    start_source = "none"
    ports_source = "none"
    start_reason = ""
    ports_reason = ""
    matched_rules: List[str] = []

    matched_entry = _first_existing_file(scan_dir, entry_files)

    for rule in rules:
        if not isinstance(rule, dict):
            raise ConfigError(f"patterns.{stack_id}.rules 仅支持对象列表")

        is_hit, rule_hit = _rule_matches(scan_dir, rule)
        if not is_hit:
            continue

        rule_id = str(first_non_empty(rule.get("id"), "unnamed-rule"))
        infer_cfg = ensure_dict(rule.get("infer"), f"patterns.{stack_id}.rules[{rule_id}].infer")
        reason = str(first_non_empty(infer_cfg.get("reason"), rule.get("reason"), f"命中规则 {rule_id}"))

        if rule_hit and not matched_entry and (scan_dir / rule_hit).is_file():
            matched_entry = rule_hit

        if not inferred_ports:
            ports_val = normalize_ports(infer_cfg.get("expose_ports"))
            if ports_val:
                inferred_ports = ports_val
                ports_source = "rule"
                ports_reason = reason

        if not inferred_start:
            start_tpl = first_non_empty(infer_cfg.get("start_cmd"), "")
            if isinstance(start_tpl, str) and start_tpl.strip():
                candidate = _format_start_cmd(start_tpl.strip(), matched_entry)
                if candidate:
                    inferred_start = candidate
                    start_source = "rule"
                    start_reason = reason

        matched_rules.append(rule_id)

    if not inferred_ports:
        default_ports = normalize_ports(defaults.get("expose_ports"))
        if default_ports:
            inferred_ports = default_ports
            ports_source = "default"
            ports_reason = str(first_non_empty(defaults.get("ports_reason"), "规则未命中，使用保守默认端口"))

    if not inferred_start:
        # 先尝试基于入口文件模板推断
        template_raw = defaults.get("start_cmd_template")
        template = template_raw.strip() if isinstance(template_raw, str) else ""
        if template:
            candidate = _format_start_cmd(template, matched_entry)
            if candidate:
                inferred_start = candidate
                start_source = "entry"
                start_reason = str(first_non_empty(defaults.get("start_reason"), "命中入口文件，按模板推断启动命令"))

    if not inferred_start:
        fallback_raw = defaults.get("start_cmd")
        fallback = fallback_raw.strip() if isinstance(fallback_raw, str) else ""
        if fallback:
            inferred_start = fallback
            start_source = "default"
            start_reason = str(first_non_empty(defaults.get("start_reason"), "规则未命中，使用保守默认启动命令"))

    return {
        "start_cmd": inferred_start,
        "start_source": start_source,
        "start_reason": start_reason,
        "ports": inferred_ports,
        "ports_source": ports_source,
        "ports_reason": ports_reason,
        "entry_file": matched_entry,
        "matched_rules": matched_rules,
    }


def detect_stack(
    scan_dir: Path,
    stacks: Dict[str, Dict[str, Any]],
) -> Tuple[Optional[str], float, List[Dict[str, Any]]]:
    """根据 stacks.yaml 检测栈，返回 (best_id, confidence, details)。"""
    details: List[Dict[str, Any]] = []

    for stack_id, stack_info in stacks.items():
        detect = ensure_dict(stack_info.get("detect"), f"{stack_id}.detect")
        files = [str(x) for x in ensure_list(detect.get("any_of_files"), f"{stack_id}.detect.any_of_files")]
        dirs = [str(x) for x in ensure_list(detect.get("any_of_dirs"), f"{stack_id}.detect.any_of_dirs")]

        file_hits = [name for name in files if (scan_dir / name).exists()]
        dir_hits = [name for name in dirs if (scan_dir / name).is_dir()]

        # 文件命中是主信号；目录命中只做置信增强。
        score = len(file_hits) * 10 + len(dir_hits) * 3
        max_score = max(1, len(files) * 10 + len(dirs) * 3)

        # 额外内容信号：减少 python/ai、web/pwn 等相似目录的误判。
        if stack_id == "ai":
            req = scan_dir / "requirements.txt"
            if req.is_file():
                try:
                    req_content = req.read_text(encoding="utf-8", errors="ignore").lower()
                except Exception:
                    req_content = ""
                if "transformers" in req_content or "torch" in req_content:
                    score += 8
                    max_score += 8

        if stack_id == "pwn":
            for cfg_name in ("ctf.xinetd", "xinetd.conf"):
                cfg = scan_dir / cfg_name
                if cfg.is_file():
                    try:
                        cfg_content = cfg.read_text(encoding="utf-8", errors="ignore").lower()
                    except Exception:
                        cfg_content = ""
                    if "service" in cfg_content and "port" in cfg_content:
                        score += 8
                        max_score += 8
                        break

        confidence = score / max_score

        details.append(
            {
                "id": stack_id,
                "score": score,
                "confidence": confidence,
                "file_hits": file_hits,
                "dir_hits": dir_hits,
                "max_score": max_score,
            }
        )

    details.sort(key=lambda x: (x["score"], len(x["file_hits"]), x["confidence"]), reverse=True)

    if not details or details[0]["score"] <= 0:
        return None, 0.0, details

    return str(details[0]["id"]), float(details[0]["confidence"]), details


def validate_rendered(
    docker_text: str,
    start_text: str,
    workdir: str,
    start_mode: str,
) -> None:
    docker_requirements = [
        "COPY start.sh /start.sh",
        "COPY flag /flag",
        "chmod 555 /start.sh",
        "chmod 444 /flag",
        "EXPOSE ",
    ]

    missing = [item for item in docker_requirements if item not in docker_text]
    if missing:
        raise ConfigError("生成的 Dockerfile 缺少硬性内容: " + ", ".join(missing))

    if not start_text.startswith("#!/bin/bash\n"):
        raise ConfigError("生成的 start.sh 第一行必须是 #!/bin/bash")

    if "set -euo pipefail" not in start_text:
        raise ConfigError("生成的 start.sh 缺少 set -euo pipefail")

    if f'cd "{workdir}"' not in start_text and f"cd {workdir}" not in start_text:
        raise ConfigError("生成的 start.sh 与 WORKDIR 不一致（缺少对应 cd）")

    if start_mode == "cmd":
        has_exec = any(line.strip().startswith("exec ") for line in start_text.splitlines())
        if not has_exec:
            raise ConfigError("单服务模式（cmd）必须 exec 主进程")
