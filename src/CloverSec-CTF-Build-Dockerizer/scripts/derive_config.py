#!/usr/bin/env python3
"""根据项目目录自动推断 challenge 配置提案（AI 编排模式使用）。"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
DATA_DIR = SKILL_ROOT / "data"

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from utils import (  # noqa: E402
    ConfigError,
    detect_stack,
    ensure_dict,
    infer_runtime_profile_candidates,
    infer_from_patterns,
    load_patterns,
    load_runtime_profiles,
    load_stack_defs,
    normalize_ports,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="推导 challenge 配置提案（JSON/YAML）")
    parser.add_argument("--project-dir", default=".", help="项目目录，默认当前目录")
    parser.add_argument("--format", choices=["json", "yaml"], default="json", help="输出格式")
    parser.add_argument("--output", default="-", help="输出文件路径，默认 stdout")
    parser.add_argument("--pretty", action="store_true", help="JSON 输出格式化")
    return parser.parse_args()


def _as_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(v) for v in value if str(v).strip()]
    return []


def _find_first_existing(scan_dir: Path, candidates: List[str]) -> Optional[str]:
    for c in candidates:
        if (scan_dir / c).exists():
            return c
    return None


def _read_package_start(scan_dir: Path) -> Optional[str]:
    pkg = scan_dir / "package.json"
    if not pkg.is_file():
        return None

    try:
        raw = json.loads(pkg.read_text(encoding="utf-8"))
    except Exception:
        return None

    scripts = raw.get("scripts") if isinstance(raw, dict) else None
    if not isinstance(scripts, dict):
        return None

    start_cmd = scripts.get("start")
    if isinstance(start_cmd, str) and start_cmd.strip():
        return "npm run start"
    return None


def _requirements_contains(scan_dir: Path, needle: str) -> bool:
    req = scan_dir / "requirements.txt"
    if not req.is_file():
        return False
    try:
        content = req.read_text(encoding="utf-8", errors="ignore").lower()
    except Exception:
        return False
    return needle.lower() in content


def _file_contains(scan_dir: Path, rel_path: str, pattern: str) -> bool:
    path = scan_dir / rel_path
    if not path.is_file():
        return False
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return False
    try:
        return re.search(pattern, content, flags=re.IGNORECASE | re.MULTILINE) is not None
    except re.error:
        return False


def _extract_xinetd_port(scan_dir: Path) -> Optional[Tuple[str, str]]:
    """从 xinetd 配置中提取端口。"""
    candidates = ["ctf.xinetd", "xinetd.conf", "etc/xinetd.d/ctf"]
    port_re = re.compile(r"\bport\s*=\s*([0-9]{1,5})\b")

    for rel in candidates:
        path = scan_dir / rel
        if not path.is_file():
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        for line in content.splitlines():
            clean = line.split("#", 1)[0]
            m = port_re.search(clean)
            if not m:
                continue
            value = m.group(1)
            if value.isdigit() and 1 <= int(value) <= 65535:
                return value, rel
    return None


def _unique_candidates(items: List[Dict[str, Any]], limit: int = 3) -> List[Dict[str, Any]]:
    seen = set()
    out: List[Dict[str, Any]] = []
    for item in items:
        cmd = str(item.get("cmd", "")).strip()
        if not cmd or cmd in seen:
            continue
        seen.add(cmd)
        out.append(
            {
                "cmd": cmd,
                "rationale": str(item.get("rationale", "")),
                "evidence": [str(x) for x in item.get("evidence", []) if str(x).strip()],
            }
        )
        if len(out) >= limit:
            break
    return out


def _build_start_candidates(
    scan_dir: Path,
    stack_id: str,
    defaults: Dict[str, Any],
    infer_info: Dict[str, Any],
    ports: List[str],
) -> Tuple[List[Dict[str, Any]], List[str]]:
    candidates: List[Dict[str, Any]] = []
    notes: List[str] = []

    inferred_cmd = str(infer_info.get("start_cmd") or "").strip()
    if inferred_cmd:
        candidates.append(
            {
                "cmd": inferred_cmd,
                "rationale": "按 patterns 规则推断",
                "evidence": [
                    f"start_source={infer_info.get('start_source', 'unknown')}",
                    str(infer_info.get("start_reason", "")).strip(),
                ],
            }
        )

    default_cmd = str(defaults.get("start_cmd") or "").strip()

    if stack_id == "node":
        if (scan_dir / "nest-cli.json").is_file() or _file_contains(
            scan_dir, "package.json", r"@nestjs/core|\"start:prod\""
        ):
            candidates.append(
                {
                    "cmd": "npm run start:prod",
                    "rationale": "命中 NestJS 工程信号",
                    "evidence": ["命中文件: nest-cli.json/package.json(@nestjs/core)"],
                }
            )

        if (scan_dir / "pnpm-workspace.yaml").is_file():
            candidates.append(
                {
                    "cmd": "pnpm -r --parallel start",
                    "rationale": "命中 pnpm workspace 结构",
                    "evidence": ["命中文件: pnpm-workspace.yaml"],
                }
            )

        pkg_cmd = _read_package_start(scan_dir)
        if pkg_cmd:
            candidates.append(
                {
                    "cmd": pkg_cmd,
                    "rationale": "检测到 package.json scripts.start",
                    "evidence": ["命中文件: package.json"],
                }
            )

        entry = _find_first_existing(scan_dir, ["server.js", "app.js", "index.js"])
        if entry:
            candidates.append(
                {
                    "cmd": f"node {entry}",
                    "rationale": "命中 Node 常见入口文件",
                    "evidence": [f"命中文件: {entry}"],
                }
            )
        else:
            notes.append("未命中 server.js/app.js/index.js，Q4 请手动确认启动命令。")

    elif stack_id == "python":
        if _requirements_contains(scan_dir, "fastapi") or _requirements_contains(
            scan_dir, "uvicorn"
        ) or _file_contains(scan_dir, "pyproject.toml", r"fastapi|uvicorn|\[tool\.poetry\]"):
            py_port = ports[0] if ports else "8000"
            candidates.append(
                {
                    "cmd": f"uvicorn main:app --host 0.0.0.0 --port {py_port}",
                    "rationale": "命中 FastAPI/Uvicorn/Poetry 依赖信号",
                    "evidence": ["命中文件: requirements.txt/pyproject.toml"],
                }
            )

        if (scan_dir / "manage.py").is_file():
            django_port = ports[0] if ports else "8000"
            candidates.append(
                {
                    "cmd": f"python manage.py runserver 0.0.0.0:{django_port}",
                    "rationale": "命中 Django manage.py",
                    "evidence": ["命中文件: manage.py"],
                }
            )

        for entry in ["app.py", "wsgi.py", "main.py"]:
            if (scan_dir / entry).is_file():
                candidates.append(
                    {
                        "cmd": f"python {entry}",
                        "rationale": "命中 Python 常见入口文件",
                        "evidence": [f"命中文件: {entry}"],
                    }
                )
                break

        if _requirements_contains(scan_dir, "gunicorn"):
            py_port = ports[0] if ports else "5000"
            candidates.append(
                {
                    "cmd": f"gunicorn -b 0.0.0.0:{py_port} app:app",
                    "rationale": "requirements.txt 检测到 gunicorn",
                    "evidence": ["命中文件: requirements.txt"],
                }
            )

    elif stack_id == "java":
        build_jar = _find_first_existing(
            scan_dir,
            [
                "target/app.jar",
                "build/libs/app.jar",
            ],
        )
        if not build_jar:
            target_glob = sorted(scan_dir.glob("target/*.jar"))
            libs_glob = sorted(scan_dir.glob("build/libs/*.jar"))
            selected = target_glob[0] if target_glob else (libs_glob[0] if libs_glob else None)
            if selected:
                try:
                    build_jar = str(selected.relative_to(scan_dir))
                except ValueError:
                    build_jar = str(selected)

        if build_jar:
            candidates.append(
                {
                    "cmd": f"java -jar {build_jar}",
                    "rationale": "命中 Java/Spring Boot 构建产物",
                    "evidence": [f"命中文件: {build_jar}"],
                }
            )

        if (scan_dir / "app.jar").is_file():
            candidates.append(
                {
                    "cmd": "java -jar app.jar",
                    "rationale": "命中可运行 JAR",
                    "evidence": ["命中文件: app.jar"],
                }
            )
        if (scan_dir / "target" / "app.jar").is_file():
            candidates.append(
                {
                    "cmd": "java -jar target/app.jar",
                    "rationale": "命中 target 目录 JAR",
                    "evidence": ["命中文件: target/app.jar"],
                }
            )
        if not (scan_dir / "app.jar").is_file() and not (scan_dir / "target" / "app.jar").is_file():
            notes.append("未检测到 app.jar/target/app.jar，Q4 请确认启动命令和制品路径。")

    elif stack_id == "tomcat":
        if (scan_dir / "ROOT.war").is_file():
            candidates.append(
                {
                    "cmd": "catalina.sh run",
                    "rationale": "命中 ROOT.war，Tomcat 前台启动",
                    "evidence": ["命中文件: ROOT.war"],
                }
            )
        else:
            candidates.append(
                {
                    "cmd": "catalina.sh run",
                    "rationale": "Tomcat 默认前台启动",
                    "evidence": ["来源: stacks.yaml defaults"],
                }
            )
            notes.append("未检测到 ROOT.war，Q5 请确认 app_src/app_dst。")

    elif stack_id == "php":
        candidates.append(
            {
                "cmd": "apache2-foreground",
                "rationale": "PHP Apache 镜像默认前台命令",
                "evidence": ["来源: stacks.yaml defaults"],
            }
        )

    elif stack_id == "lamp":
        candidates.append(
            {
                "cmd": "apache2ctl -D FOREGROUND",
                "rationale": "LAMP 主服务前台命令",
                "evidence": ["来源: stacks.yaml defaults"],
            }
        )

    elif stack_id == "pwn":
        xport = _extract_xinetd_port(scan_dir)
        if xport:
            candidates.append(
                {
                    "cmd": "/usr/sbin/xinetd -dontfork",
                    "rationale": "命中 xinetd 配置，采用 xinetd 前台启动",
                    "evidence": [f"命中文件: {xport[1]}", f"配置端口: {xport[0]}"],
                }
            )
        if (scan_dir / "bin" / "chall").is_file() or (scan_dir / "chall").is_file():
            candidates.append(
                {
                    "cmd": "/usr/sbin/xinetd -dontfork",
                    "rationale": "命中 Pwn 常见制品，推荐 xinetd 前台运行",
                    "evidence": ["命中文件: bin/chall 或 chall"],
                }
            )
        notes.append("Pwn 默认按 xinetd 前台模式交付，需确认挑战程序与 ctf.xinetd 路径一致。")

    elif stack_id == "ai":
        ai_port = ports[0] if ports else "5000"
        candidates.append(
            {
                "cmd": f"gunicorn -w 1 --threads 1 -b 0.0.0.0:{ai_port} app:app",
                "rationale": "AI 服务默认推荐 gunicorn 单进程单线程前台",
                "evidence": ["来源: AI 默认策略", "高核心环境建议收紧线程"],
            }
        )

        for entry in ["app.py", "wsgi.py", "main.py"]:
            if (scan_dir / entry).is_file():
                candidates.append(
                    {
                        "cmd": f"python {entry}",
                        "rationale": "命中 AI 常见入口文件",
                        "evidence": [f"命中文件: {entry}"],
                    }
                )
                break

        if _requirements_contains(scan_dir, "transformers"):
            candidates.append(
                {
                    "cmd": f"gunicorn -w 1 --threads 1 -b 0.0.0.0:{ai_port} app:app",
                    "rationale": "requirements 检测到 transformers，建议限制并发",
                    "evidence": ["命中文件: requirements.txt", "命中关键字: transformers"],
                }
            )
        notes.append("AI 栈建议设置 OPENBLAS/OMP/MKL 线程限制，避免高核心宿主机线程创建失败。")

    elif stack_id == "rdg":
        if (scan_dir / "index.php").is_file() or (scan_dir / "composer.json").is_file():
            candidates.append(
                {
                    "cmd": "apache2-foreground",
                    "rationale": "命中 PHP Web 特征，优先 Apache 前台启动",
                    "evidence": ["命中文件: index.php/composer.json"],
                }
            )

        if (scan_dir / "app.py").is_file():
            candidates.append(
                {
                    "cmd": "python app.py",
                    "rationale": "命中 Python 入口文件",
                    "evidence": ["命中文件: app.py"],
                }
            )

        if (scan_dir / "requirements.txt").is_file():
            candidates.append(
                {
                    "cmd": "python app.py",
                    "rationale": "命中 requirements.txt，按轻量 Web 服务推断",
                    "evidence": ["命中文件: requirements.txt"],
                }
            )

        candidates.append(
            {
                "cmd": "bash -lc 'if command -v apache2-foreground >/dev/null 2>&1; then exec apache2-foreground; elif command -v python3 >/dev/null 2>&1; then exec python3 app.py; elif command -v python >/dev/null 2>&1; then exec python app.py; elif command -v nginx >/dev/null 2>&1; then exec nginx -g \"daemon off;\"; else exec /bin/bash; fi'",
                "rationale": "RDG 兼容回退命令（按运行环境自动选择主服务）",
                "evidence": ["来源: patterns.yaml defaults.start_cmd"],
            }
        )
        notes.append("RDG 默认启用 ttyd+sshd 双通道，并创建 ctf 用户（默认口令 123456）。")
        notes.append("RDG 默认采用 check-service 判定；如无需登录链路可显式关闭 enable_ttyd/enable_sshd。")

    if default_cmd:
        candidates.append(
            {
                "cmd": default_cmd,
                "rationale": "栈默认启动命令",
                "evidence": ["来源: stacks.yaml defaults.start_cmd"],
            }
        )

    unique = _unique_candidates(candidates, limit=3)
    entry_hint = str(infer_info.get("entry_file") or "").strip()
    entry_sensitive_stacks = {"node", "python", "java", "tomcat", "ai", "rdg"}
    if stack_id in entry_sensitive_stacks and not entry_hint:
        unique.insert(
            0,
            {
                "cmd": "",
                "rationale": "未推断到可执行入口，必须手动确认启动命令",
                "evidence": [
                    "patterns 未命中有效 entry_file",
                    "为避免误生成误执行，Q4 需显式填写 start.cmd",
                ],
            },
        )
        notes.append("未推断到入口文件，Q4 不可直接回车，必须显式填写启动命令。")

    if not unique:
        notes.append("未生成可用启动命令候选，Q4 必须手动输入 start_cmd。")

    return unique, notes


def _guess_app_paths(scan_dir: Path, stack_id: str, workdir: str) -> Tuple[str, str, List[str]]:
    evidence: List[str] = []
    app_src = "."
    app_dst = workdir

    if stack_id == "tomcat":
        if (scan_dir / "ROOT.war").is_file():
            app_src = "ROOT.war"
            app_dst = "/usr/local/tomcat/webapps/ROOT.war"
            evidence.append("命中文件: ROOT.war")
        elif (scan_dir / "webapps" / "ROOT.war").is_file():
            app_src = "webapps/ROOT.war"
            app_dst = "/usr/local/tomcat/webapps/ROOT.war"
            evidence.append("命中文件: webapps/ROOT.war")
        else:
            evidence.append("未命中 WAR，回退 app_src='.' -> app_dst=WORKDIR")
    elif stack_id == "pwn":
        if (scan_dir / "bin").is_dir():
            app_src = "."
            app_dst = "/home/ctf"
            evidence.append("命中目录: bin，Pwn 默认复制到 /home/ctf")
        else:
            evidence.append("未命中 bin 目录，回退 app_src='.' -> app_dst=WORKDIR")
    elif stack_id == "rdg":
        app_src = "."
        app_dst = "/app"
        evidence.append("RDG 模式默认复制整个题目目录到 /app，兼容多种源码布局")
    else:
        evidence.append("按通用约定 app_src='.' -> app_dst=WORKDIR")

    return app_src, app_dst, evidence


def derive(project_dir: Path) -> Dict[str, Any]:
    stacks = load_stack_defs(DATA_DIR / "stacks.yaml")
    patterns = load_patterns(DATA_DIR / "patterns.yaml")
    runtime_profiles = load_runtime_profiles(DATA_DIR / "runtime_profiles.yaml")

    best_id, best_conf, details = detect_stack(project_dir, stacks)
    if best_id:
        stack_id = best_id
    elif details:
        stack_id = str(details[0]["id"])
        best_conf = float(details[0]["confidence"])
    else:
        stack_id = "node"
        best_conf = 0.0

    stack_detail = next((d for d in details if d["id"] == stack_id), None)
    stack_info = ensure_dict(stacks.get(stack_id), f"stacks[{stack_id}]")
    defaults = ensure_dict(stack_info.get("defaults"), f"stacks[{stack_id}].defaults")

    infer_info = infer_from_patterns(project_dir, stack_id, patterns)
    runtime_info = infer_runtime_profile_candidates(project_dir, stack_id, runtime_profiles)
    inferred_base_image_raw = infer_info.get("base_image")
    inferred_base_image = (
        inferred_base_image_raw.strip() if isinstance(inferred_base_image_raw, str) else ""
    )

    guessed_ports = normalize_ports(infer_info.get("ports"))
    ports_from_default = False
    port_evidence: List[str] = []
    xinetd_port = _extract_xinetd_port(project_dir) if stack_id == "pwn" else None
    if xinetd_port:
        guessed_ports = [xinetd_port[0]]
        port_evidence.append("来源: xinetd 配置解析")
        port_evidence.append(f"命中文件: {xinetd_port[1]}（port={xinetd_port[0]}）")

    if guessed_ports:
        if not xinetd_port:
            port_evidence.append(f"来源: {infer_info.get('ports_source', 'rule')}")
            reason = str(infer_info.get("ports_reason", "")).strip()
            if reason:
                port_evidence.append(reason)
    else:
        guessed_ports = normalize_ports(defaults.get("expose_ports"))
        ports_from_default = True
        port_evidence.append("回退: stacks.yaml defaults.expose_ports")

    workdir = str(defaults.get("workdir") or "/app")
    workdir_evidence = ["来源: stacks.yaml defaults.workdir"]

    candidates, candidate_notes = _build_start_candidates(project_dir, stack_id, defaults, infer_info, guessed_ports)

    app_src, app_dst, app_path_evidence = _guess_app_paths(project_dir, stack_id, workdir)

    notes: List[str] = [
        "确保服务监听 0.0.0.0，避免容器内可达但外部不可达。",
        "单服务启动命令必须以前台 exec 方式运行。",
    ]
    notes.extend(candidate_notes)

    if best_conf < 0.6:
        notes.append(f"栈侦测置信度较低（{best_conf:.2f}），Q1 请重点确认技术栈。")

    if not candidates:
        notes.append("未找到启动命令候选，Q4 必须手动输入 start_cmd。")
    elif not candidates[0].get("cmd", "").strip():
        notes.append("启动命令候选为空占位，Q4 必须填写可执行命令。")

    if inferred_base_image:
        notes.append(
            "基础镜像按 patterns 推断为 {}（source={}）。".format(
                inferred_base_image, infer_info.get("base_image_source", "rule")
            )
        )
    if runtime_info.get("supported"):
        notes.append(
            "Q1 请同时确认技术栈与运行时档位（recommended_profile={} -> {}）。".format(
                runtime_info.get("recommended_profile", ""),
                runtime_info.get("recommended_base_image", ""),
            )
        )

    stack_evidence: List[str] = []
    if stack_detail:
        file_hits = _as_list(stack_detail.get("file_hits"))
        dir_hits = _as_list(stack_detail.get("dir_hits"))
        if file_hits:
            stack_evidence.append("命中文件: " + ", ".join(file_hits))
        if dir_hits:
            stack_evidence.append("命中目录: " + ", ".join(dir_hits))
        stack_evidence.append(
            "score={}/{}".format(stack_detail.get("score", 0), stack_detail.get("max_score", 1))
        )
    else:
        stack_evidence.append("未命中明确特征，使用默认栈回退")

    requires_explicit_stack_confirm = best_conf < 0.6
    requires_port_confirm = ports_from_default or infer_info.get("ports_source") in {"none", "default"}
    requires_start_cmd_confirm = (
        not candidates
        or not str(candidates[0].get("cmd", "")).strip()
        or infer_info.get("start_source") in {"none", "default", "entry"}
    )

    default_healthcheck_cmd = str(defaults.get("healthcheck_cmd") or "").strip()

    proposal_base_image = inferred_base_image or str(defaults.get("base_image") or "")
    if runtime_info.get("supported") and str(runtime_info.get("recommended_base_image", "")).strip():
        proposal_base_image = str(runtime_info.get("recommended_base_image")).strip()

    proposal: Dict[str, Any] = {
        "stack_guess": {
            "id": stack_id,
            "confidence": round(best_conf, 4),
            "evidence": stack_evidence,
        },
        "port_guess": {
            "ports": guessed_ports,
            "evidence": port_evidence,
        },
        "workdir_guess": {
            "workdir": workdir,
            "evidence": workdir_evidence,
        },
        "start_cmd_candidates": candidates,
        "app_paths": {
            "app_src": app_src,
            "app_dst": app_dst,
            "evidence": app_path_evidence,
        },
        "gates": {
            "requires_explicit_stack_confirm": requires_explicit_stack_confirm,
            "requires_start_cmd_confirm": requires_start_cmd_confirm,
            "requires_port_confirm": requires_port_confirm,
        },
        "notes": notes,
        "runtime_profile_candidates": runtime_info.get("candidates", []),
        "recommended_profile": runtime_info.get("recommended_profile", ""),
        "recommended_base_image": runtime_info.get("recommended_base_image", ""),
        "runtime_profile_evidence": runtime_info.get("evidence", []),
        # 供 AI 直接渲染 Step 1 的 CONFIG PROPOSAL 块
        "config_proposal": {
            "stack": stack_id,
            "base_image": proposal_base_image,
            "workdir": workdir,
            "app_src": app_src,
            "app_dst": app_dst,
            "expose_ports": guessed_ports,
            "start": {
                "mode": "cmd",
                "cmd": candidates[0]["cmd"] if candidates else "",
            },
            "platform": {
                "entrypoint": "/start.sh",
                "require_bash": True,
                "allow_loopback_bind": False,
            },
            "flag": {
                "path": "/flag",
                "permission": "444",
            },
            "healthcheck": {
                "enabled": True,
                "cmd": default_healthcheck_cmd,
                "interval": "30s",
                "timeout": "5s",
                "retries": 3,
                "start_period": "10s",
            },
        },
    }

    if stack_id == "rdg":
        rdg_ports = list(guessed_ports)
        for p in ["8022", "22"]:
            if p not in rdg_ports:
                rdg_ports.append(p)
        proposal["port_guess"]["ports"] = rdg_ports
        proposal["config_proposal"]["expose_ports"] = rdg_ports
        proposal["config_proposal"]["rdg"] = {
            "enable_ttyd": True,
            "ttyd_port": "8022",
            "ttyd_login_cmd": "/bin/bash",
            "enable_sshd": True,
            "sshd_port": "22",
            "sshd_password_auth": True,
            "ttyd_binary_relpath": "ttyd",
            "ttyd_install_fallback": True,
            "ctf_user": "ctf",
            "ctf_password": "123456",
            "ctf_in_root_group": False,
            "scoring_mode": "check_service",
            "include_flag_artifact": True,
            "check_enabled": True,
            "check_script_path": "check/check.sh",
        }

    return proposal


def write_output(data: Dict[str, Any], fmt: str, output: str, pretty: bool) -> None:
    if fmt == "yaml":
        try:
            import yaml
        except ModuleNotFoundError as exc:
            raise ConfigError("输出 YAML 需要 PyYAML，请先安装 requirements.txt") from exc
        rendered = yaml.safe_dump(data, sort_keys=False, allow_unicode=True)
    else:
        rendered = json.dumps(data, ensure_ascii=False, indent=2 if pretty or output == "-" else None)
        if pretty or output == "-":
            rendered += "\n"

    if output == "-":
        sys.stdout.write(rendered)
        return

    out_path = Path(output).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(rendered, encoding="utf-8")


def main() -> int:
    args = parse_args()
    project_dir = Path(args.project_dir).resolve()

    try:
        proposal = derive(project_dir)
        write_output(proposal, args.format, args.output, args.pretty)
        return 0
    except ConfigError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
