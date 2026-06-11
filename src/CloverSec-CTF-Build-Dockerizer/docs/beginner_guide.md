# CloverSec-CTF-Build-Dockerizer 新手实战使用指南（Codex / Claude / Trae）

本指南面向第一次接触该 Skill 的同学，目标是让你不看源码也能完成：

1. 在对话里正确触发 Skill
2. 用最少交互生成可交付的 `Dockerfile + start.sh + changeflag.sh + flag(可选)`
3. 在真实业务场景中稳定复用

## 目录

- 1. 先知道它能做什么
- 2. 平台硬约束（必须满足）
- 3. 三个平台如何触发这个 Skill
- 4. 新手最推荐对话模式（AI Orchestrated）
- 5. 真实业务场景怎么触发
- 6. 手动模式（当你不走对话工作流时）
- 7. 小白常见误区
- 8. 你下一步该做什么

## 1. 先知道它能做什么

`CloverSec-CTF-Build-Dockerizer` 用于把题目目录、组件目录或本地场景定义转换为当前平台契约下可运行、可校验的容器交付物。当前核心能力覆盖：

- Jeopardy / Web / Pwn / AI
- RDG / AWD / AWDP / SecOps
- BaseUnit 纯基座组件渲染
- Linux-QEMU 内核题环境渲染
- Scenario 本地多服务编排

主链路是：

1. 自动探测栈与启动信息（`derive_config.py`）
2. 输出配置确认块（`CONFIG PROPOSAL`）
3. 你只需要回复 `OK` 或改一行 YAML
4. AI 自动执行渲染与校验（`parse_config_block.py -> render.py -> validate.sh`）

渲染最小产物固定为：

- `Dockerfile`
- `start.sh`
- `changeflag.sh`
- `flag`（按 profile / defense 配置可选）

## 2. 平台硬约束（必须满足）

无论哪个 Agent（Codex / Claude / Trae），都必须满足同一平台约束：

1. 平台固定用 `/start.sh` 启动：`docker run -d -p host:container <image>:latest /start.sh`
2. 镜像必须包含 `/start.sh` 且可执行
3. 镜像必须包含 `/changeflag.sh` 且可执行
4. 镜像必须包含 `/bin/bash`（平台会执行 `/bin/bash /changeflag.sh`）
5. Dockerfile 必须有 `EXPOSE`
6. 禁止空转保活（`sleep infinity`、`while true; do sleep ...`）
7. 单服务必须 `exec` 主进程（PID1）
8. `/flag` 默认要求存在；仅在支持的 defense profile 中显式设置 `include_flag_artifact=false` 时可放行

## 3. 三个平台如何触发这个 Skill

核心原则：如果没有自动触发，就在提示词里明确写 `CloverSec-CTF-Build-Dockerizer`，并要求走 `CONFIG PROPOSAL -> OK -> 生成` 流程。

### 3.1 Codex 触发示例

```text
请使用 CloverSec-CTF-Build-Dockerizer 处理当前题目目录。
先执行自动探测并输出 CONFIG PROPOSAL，我确认 OK 后你再自动生成 Dockerfile/start.sh/changeflag.sh/flag(可选)，并运行 validate。
```

### 3.2 Claude 触发示例

```text
使用 CloverSec-CTF-Build-Dockerizer skill 对当前目录做容器化。
按 5 个确认项给出 CONFIG PROPOSAL，我回复 OK 后再执行 render 和 validate。
```

### 3.3 Trae 触发示例

```text
使用 CloverSec-CTF-Build-Dockerizer 工作流：derive -> CONFIG PROPOSAL -> parse -> render -> validate。
先给我 YAML 确认块，我只回复 OK。
```

## 4. 新手最推荐对话模式（AI Orchestrated）

你和 AI 的最小交互应当是：

1. AI 自动探测项目
2. AI 给出 `CONFIG PROPOSAL` YAML
3. 你回复 `OK`（或只改 YAML 某一行）
4. AI 自动生成并校验

你只需要关注这 5 个确认项：

1. 技术栈 + profile（php/node/java 还要确认运行时档位）
2. 容器端口
3. `WORKDIR`
4. 启动命令
5. `app_src -> app_dst`

完整 `CONFIG PROPOSAL` 模板、OK 门槛、gates 处理和失败保护规则见 `docs/orchestrated_workflow.md`。

## 5. 真实业务场景怎么触发

| 场景 | 触发语句（可直接发给 AI） | 期望输出 |
|---|---|---|
| 老题目没有 Dockerfile | “用 CloverSec-CTF-Build-Dockerizer 为当前目录生成交付文件，按 CONFIG PROPOSAL 流程走。” | 生成 `Dockerfile/start.sh/changeflag.sh/flag(可选)` |
| 题目容器一启动就退出 | “用 CloverSec-CTF-Build-Dockerizer 重生 start.sh，并确保单服务用 exec 作为 PID1。” | `start.sh` 可持续运行且有日志 |
| 平台报 `/bin/bash` 不存在 | “用 CloverSec-CTF-Build-Dockerizer 修复镜像，确保 /bin/bash 可用并通过 validate。” | Dockerfile 补齐 bash 安装 |
| 平台动态 flag 写入失败 | “检查并修复 /flag 权限、路径与 changeflag 入口约束。” | `/flag` 与 `/changeflag.sh` 约束正确 |
| 端口映射后访问不到 | “检查 EXPOSE 与服务监听地址，确保监听 0.0.0.0 并更新配置。” | 端口与监听修复 |
| Pwn 题目需要前台托管 | “按 pwn 栈生成模板，并确保 start.sh 使用 xinetd/tcpserver/socat 的合法前台路径。” | 端口/前台策略符合平台约束 |
| AI 题目在高核心服务器报线程错误 | “按 ai 栈生成并设置 OPENBLAS/OMP/MKL 线程限制，使用 gunicorn 单 worker。” | 线程稳定、容器持续运行 |
| 需要生成纯组件镜像 | “用 render_component.py 生成 baseunit 组件目录，并保留平台契约文件。” | 输出可直接 `docker build` 的目录 |
| 需要本地多服务演练 | “用 scenario.yaml 渲染本地场景，并校验 profile/端口/AWDP 补丁契约。” | 服务目录 + `docker-compose.yml` |

## 6. 手动模式（当你不走对话工作流时）

```bash
# 1) 自动提案（可选）
python3 scripts/derive_config.py --project-dir . --format json --pretty

# 2) 渲染
python3 scripts/render.py --config challenge.yaml --output .

# 3) 静态校验
bash scripts/validate.sh Dockerfile start.sh challenge.yaml

# 4) 本地构建与运行（平台等价）
docker build -t ctf-web-demo:latest .
docker run -d -p 8080:80 ctf-web-demo:latest /start.sh
docker logs -f "$(docker ps -q --filter ancestor=ctf-web-demo:latest | head -n 1)"
```

## 7. 小白常见误区

1. 把宿主机端口写进 `expose_ports`
2. 启动命令只监听 `127.0.0.1`
3. 用 `sleep infinity` 保活
4. 忘了 `/start.sh`、`/changeflag.sh` 或 `/bin/bash`
5. 把 `include_flag_artifact=false` 理解成可以跳过所有平台产物
6. 忽略 `validate.sh`

## 8. 你下一步该做什么

1. 复制触发示例发给 Agent。
2. 收到 `CONFIG PROPOSAL` 后只回复 `OK` 或改 YAML。
3. 查看 `Dockerfile/start.sh/changeflag.sh/flag(可选)` 与 validate 结果。
4. 需要运行时，再本地 `docker run ... /start.sh` 验证。
