# AI 编排确认协议（v2.2.0）

本文档承接旧版 `SKILL.md` 中的 `AI Orchestrated Mode` 详细规则。入口文件只保留硬门槛，完整提案格式按需读取本文档。

## 目录

- 1. 总原则
- 2. Step 0：自动探测
- 3. Step 1：只问 5 个确认项
- 4. CONFIG PROPOSAL 模板
- 5. Step 2：确认后生成
- 6. Step 3：交付说明
- 7. 低交互失败保护

## 1. 总原则

本 Skill 默认运行在 AI 编排模式，目标是：用户只确认 5 项关键配置，Agent 自动完成探测、生成、校验和必要修复。

Agent 必须遵守：

- 优先执行脚本：`derive_config.py`、`parse_config_block.py`、`render.py`、`validate.sh`。
- 不要求用户自己执行命令。
- 不凭经验直接手写 Dockerfile 取代脚本输出。
- 必须向用户展示关键默认值的 evidence，例如命中文件、规则或配置来源。
- 未经用户确认，不得进入 render/validate 阶段。

## 2. Step 0：自动探测

先执行：

```bash
python3 scripts/derive_config.py --project-dir <题目目录> --format json --pretty
```

从输出中提取 proposed config，并生成 5 项配置提案摘要：

1. 技术栈猜测
2. 端口猜测
3. WORKDIR 猜测
4. 启动命令候选，最多 3 个
5. `app_src` / `app_dst` 拷贝路径建议

每项必须附带 evidence。若输出包含 `config_proposal` 字段，优先用它生成 Step 1 的 YAML 确认块。

字段来源必须分清：

- `stack_guess`、`port_guess`、`workdir_guess` 是推断结果。
- `stack_source=challenge.yaml` 或 `explicit_config.*=true` 表示已有明确配置，优先级高于自动探测。
- `detected_stack_hint` 只是复核提示，不能覆盖 `challenge.yaml` 中明确写出的 stack。
- `inference_hints` 用于提示需要人工看的线索，例如 Pwn flag 路径。

若输出包含 gates，必须执行门禁：

- `requires_explicit_stack_confirm=true`：Q1 必须显式确认 stack。
- `requires_start_cmd_confirm=true`：Q4 必须确认最终启动命令。
- `requires_port_confirm=true`：Q2 必须确认端口。

## 3. Step 1：只问 5 个确认项

固定确认项：

| 项 | 内容 | 默认来源 |
|---|---|---|
| Q1 | 技术栈 + profile / runtime profile | `derive_config.py` 的 stack 与 runtime 建议 |
| Q2 | 容器端口 | `port_guess.ports` 或栈默认端口 |
| Q3 | WORKDIR | `workdir_guess.workdir` |
| Q4 | 启动命令 | 启动候选 #1，候选 #2/#3 作为备选 |
| Q5 | 代码拷贝路径 | `app_src="." -> app_dst=WORKDIR` |

不能追加第 6 个问题，除非输入明显冲突且无法继续。

固定输出结构：

```text
【配置提案摘要】
1) 栈: <stack_guess.id>（confidence=<x.xx>，evidence: <...>）
2) 端口: <ports>（evidence: <...>）
3) WORKDIR: <workdir>（evidence: <...>）
4) 启动候选:
   - #1 <cmd1>（evidence: <...>）
   - #2 <cmd2>（evidence: <...>）
   - #3 <cmd3>（evidence: <...>）
5) 拷贝路径: <app_src> -> <app_dst>（evidence: <...>）
```

随后输出 `CONFIG PROPOSAL` YAML。

Pwn 题必须额外说明业务 flag 路径来源：

- 若输出包含 `pwn_flag_path_hints`，把命中的文件、行号和候选路径列出来，并要求用户确认 `flag.sync_paths`。
- 若没有命中线索，也要提示用户看源码或 PoC，确认程序读取 `/flag`、`/home/ctf/flag`、`flag0/flag1` 还是其他路径。
- 源码里的相对路径要按 WORKDIR 转成绝对路径，例如 WORKDIR 为 `/home/ctf` 时，`flag0` 应写成 `/home/ctf/flag0`。
- 不得把默认 `/home/ctf/flag` 描述为所有 Pwn 题都正确。

## 4. CONFIG PROPOSAL 模板

```yaml
CONFIG PROPOSAL:
  stack: <node|php|python|java|tomcat|lamp|pwn|ai|rdg|secops|baseunit|linux-qemu>
  profile: <jeopardy|rdg|awd|awdp|secops>
  base_image: <string|optional>
  workdir: <string>
  app_src: <string>
  app_dst: <string>
  expose_ports: [<port>, ...]
  start:
    mode: cmd
    cmd: "<string>"
  platform:
    entrypoint: "/start.sh"
    require_bash: true
    allow_loopback_bind: false
  flag:
    path: "/flag"
    permission: "444"
  healthcheck:
    enabled: true
    cmd: "bash -lc 'echo > /dev/tcp/127.0.0.1/80'"
    interval: "30s"
    timeout: "5s"
    retries: 3
    start_period: "10s"
  defense:
    enable_ttyd: true
    ttyd_port: "8022"
    ttyd_login_cmd: "/bin/bash"
    enable_sshd: true
    sshd_port: "22"
    sshd_password_auth: true
    ttyd_binary_relpath: "ttyd"
    ttyd_install_fallback: true
    ctf_user: "ctf"
    ctf_password: "123456"
    ctf_in_root_group: false
    scoring_mode: "check_service"
    include_flag_artifact: true
    check_enabled: true
    check_script_path: "check/check.sh"
  rdg:
    enable_ttyd: true
    ttyd_port: "8022"
    enable_sshd: true
    sshd_port: "22"
```

YAML 块后必须输出：

```text
如果以上配置正确，请回复：OK

如果需要修改，请直接在上面的 YAML 块里改对应行并发回（不要额外解释），我会按你修改后的配置继续生成与校验。
```

## 5. Step 2：确认后生成

进入生成阶段的条件只有两种：

- 用户回复 `OK`
- 用户返回可解析的 `CONFIG PROPOSAL` YAML

其他散乱文本都不能触发 render。应提示用户回复 `OK` 或粘贴修改后的 YAML。

确认后执行：

```bash
cat <project_dir>/config-proposal.yaml | python3 scripts/parse_config_block.py --output <project_dir>/challenge.yaml
python3 scripts/render.py --config <project_dir>/challenge.yaml --output <project_dir>
bash scripts/validate.sh <project_dir>/Dockerfile <project_dir>/start.sh <project_dir>/challenge.yaml
```

如果 validate 出现 ERROR，Agent 必须自动修复并重跑 validate，直到 `ERROR=0` 或明确说明无法自动修复。只有 WARN 时可以继续，但必须说明影响。

如果确认后又手工修改了 `challenge.yaml`，不要直接改用 `render.py --manual`。应先登记当前配置：

```bash
python3 scripts/workflow.py accept --project-dir <project_dir> --refresh --notes "reviewed manual edits"
python3 scripts/workflow.py render --project-dir <project_dir>
```

这样会更新 accepted hash，不会重新生成 `challenge.yaml`，也能保留 proposal gate 记录。

低风险、已有明确 `challenge.yaml`，且用户已经审查方案摘要时，可以使用：

```bash
python3 scripts/workflow.py reviewed-render --project-dir <project_dir> --reason "reviewed explicit challenge.yaml"
```

`reviewed-render` 不用于跳过高风险 gate。mixed/dirty/high_risk 输入必须先完成 `propose` 和 `accept`，或已有匹配的 accepted hash。

## 6. Step 3：交付说明

交付时必须说明：

- 最终工作目录和主要产物。
- 本地测试命令：`docker build` 与 `docker run ... /start.sh`。
- 平台导入提醒：端口映射、固定 `/start.sh` 启动、动态 flag 依赖 `/bin/bash`。
- 未执行的检查，例如 Docker build、QEMU boot、PoC 复现。

## 7. 低交互失败保护

- 栈侦测置信度 `<0.6`：仍给默认值，但 Q1 必须强提示确认技术栈。
- 找不到入口文件：Q4 必须强提示填写启动命令，未确认前不得 render。
- 端口为空：可回退栈默认端口，但 Q2 必须提示确认端口。
- 启动命令可能只监听 `127.0.0.1`：必须提示改为 `0.0.0.0` 并给示例。
