---
name: CloverSec-CTF-Build-Dockerizer
description: 四叶草安全-创研中心竞赛专用题目容器构建Skills，面向 CTF Jeopardy（Web/Pwn/AI）与 RDG（Docker）模式的容器交付引擎：自动探测栈、生成合规 Dockerfile/start.sh/flag(可选)+check 脚手架、执行规则校验并给出可修复建议，实现标准化工作流程的质量对齐。
argument-hint: "[path/to/challenge.yaml] 或 --stack node|php|python|java|tomcat|lamp|pwn|ai|rdg --port 80 --start '...'"
disable-model-invocation: true
allowed-tools:
  - Bash
  - Read
  - Write
  - Glob
  - Grep
---

# CloverSec-CTF-Build-Dockerizer

**硬约束：平台固定使用 `/start.sh` 启动**

**镜像根目录默认必须包含 `/flag` 且可读（RDG 且 include_flag_artifact=false 可放行）**

**镜像中必须存在 `/bin/bash`**

**能力边界：当前支持 Jeopardy 模式（Web/Pwn/AI）与 RDG（Docker）模式，不支持 AWD/AWDP 竞赛模式编排。**

## 快速开始

1. 进入示例目录。
2. 用 `render.py` 生成 `Dockerfile/start.sh/flag(可选)+check 脚手架`。
3. 用 `validate.sh` 做静态校验。
4. 本地 `docker build`。
5. 本地 `docker run ... /start.sh`。
6. 观察日志并修复问题。

最小命令链：

```bash
cd src/CloverSec-CTF-Build-Dockerizer/examples/node-basic
python3 ../../scripts/render.py --config challenge.yaml --output .
bash ../../scripts/validate.sh Dockerfile start.sh challenge.yaml
docker build -t ctf-node-basic:latest .
docker run -d -p 3001:3000 ctf-node-basic:latest /start.sh
docker logs -f $(docker ps -q --filter ancestor=ctf-node-basic:latest | head -n 1)
```

## 文档导航

- 输入 schema：`src/CloverSec-CTF-Build-Dockerizer/data/schema.md`
- 栈默认值：`src/CloverSec-CTF-Build-Dockerizer/data/stacks.yaml`
- 推断规则：`src/CloverSec-CTF-Build-Dockerizer/data/patterns.yaml`
- 可配置校验：`src/CloverSec-CTF-Build-Dockerizer/data/validate_rules.yaml`
- 平台契约：`src/CloverSec-CTF-Build-Dockerizer/docs/platform_contract.md`
- 栈手册：`src/CloverSec-CTF-Build-Dockerizer/docs/stack_cookbook.md`
- 故障排查：`src/CloverSec-CTF-Build-Dockerizer/docs/troubleshooting.md`
- 新手指南（安装/触发/场景）：`src/CloverSec-CTF-Build-Dockerizer/docs/beginner_guide.md`

## 白皮书章节映射

- 白皮书主文档：`README.md`
- 本文件与白皮书关键对应：
  - 本文 `输入契约` <-> 白皮书 `5. 输入契约`
  - 本文 `AI Orchestrated Mode` <-> 白皮书 `6. AI Orchestrated Wizard`
  - 本文 `手动模式` <-> 白皮书 `7. 手动模式`
  - 本文 `9 栈模板索引` <-> 白皮书 `8. 九栈能力对照`
  - 本文 `validate 规则速查` <-> 白皮书 `10. 校验系统`
  - 本文 `命令速查/附录` <-> 白皮书 `12-15`

## 一句话定位

当你要把 Web、Pwn、AI 与 RDG（Docker）模式题目源码变成平台可运行镜像时，使用本技能可以稳定生成并校验交付件。

## 输入契约（challenge.yaml 字段映射）

| 字段 | 必填 | 默认值来源 | 示例 | 映射模板变量/行为 |
|---|---|---|---|---|
| `challenge.name` | 是 | 无 | `node-basic` | 用于标识题目，不直接进模板 |
| `challenge.stack` | 否 | 侦测结果 | `node` | 选择 `templates/<stack>/` |
| `challenge.base_image` | 否 | `stacks.yaml` | `node:20-alpine` | `{{BASE_IMAGE}}` |
| `challenge.workdir` | 否 | `stacks.yaml` | `/app` | `{{WORKDIR}}`，并要求 start.sh `cd` |
| `challenge.app_src` | 否 | `.` | `.` | `{{APP_SRC}}` |
| `challenge.app_dst` | 否 | `workdir` | `/app` | `{{APP_DST}}` |
| `challenge.expose_ports` | 否 | patterns -> stacks | `["3000"]` | `{{EXPOSE_PORTS}}` |
| `challenge.start.mode` | 否 | `cmd` | `cmd` | 影响 exec 校验策略 |
| `challenge.start.cmd` | 否 | patterns -> stacks | `node server.js` | `{{START_CMD}}` |
| `challenge.start.service_name` | 否 | 空 | `apache2` | 多服务描述辅助 |
| `challenge.runtime_deps` | 否 | `[]` | `["curl"]` | `{{RUNTIME_DEPS_INSTALL}}` |
| `challenge.build_deps` | 否 | `[]` | `[]` | 当前不直接渲染，保留扩展 |
| `challenge.flag.path` | 否 | `/flag` | `/flag` | 平台契约字段 |
| `challenge.flag.permission` | 否 | `444` | `444` | 平台契约字段 |
| `challenge.platform.entrypoint` | 否 | `/start.sh` | `/start.sh` | 平台契约字段 |
| `challenge.platform.require_bash` | 否 | `true` | `true` | 平台契约字段 |
| `challenge.extra.env` | 否 | `{}` | `{NODE_ENV: production}` | `{{ENV_BLOCK}}` |
| `challenge.extra.copy` | 否 | `[]` | `[{from:a,to:b}]` | `{{COPY_APP}}` |
| `challenge.extra.user` | 否 | 空 | `www-data` | 当前不直接渲染 |
| `challenge.extra.npm_install_block` | 否 | 自动生成 | `RUN npm ci ...` | `{{NPM_INSTALL_BLOCK}}` |
| `challenge.extra.pip_requirements_block` | 否 | 自动生成 | `RUN pip install ...` | `{{PIP_REQUIREMENTS_BLOCK}}` |
| `challenge.rdg.enable_sshd` | 否 | `true` | `true` | RDG sshd 登录开关 |
| `challenge.rdg.sshd_port` | 否 | `22` | `22` | RDG sshd 端口 |
| `challenge.rdg.sshd_password_auth` | 否 | `true` | `true` | RDG sshd 密码认证 |
| `challenge.rdg.ttyd_binary_relpath` | 否 | `ttyd` | `ttyd` | RDG ttyd 二进制相对路径 |
| `challenge.rdg.ttyd_install_fallback` | 否 | `true` | `true` | RDG ttyd 安装回退开关 |
| `challenge.rdg.ctf_user` | 否 | `ctf` | `ctf` | RDG 默认选手账户 |
| `challenge.rdg.ctf_password` | 否 | `123456` | `123456` | RDG 默认选手口令 |
| `challenge.rdg.ctf_in_root_group` | 否 | `false` | `false` | RDG 是否加入 root 组 |
| `challenge.rdg.scoring_mode` | 否 | `check_service` | `check_service` | RDG 判定模式 |
| `challenge.rdg.include_flag_artifact` | 否 | `true` | `false` | RDG 是否保留 `/flag` 产物 |
| `challenge.rdg.check_enabled` | 否 | `true` | `true` | RDG check 脚手架约束 |
| `challenge.rdg.check_script_path` | 否 | `check/check.sh` | `check/check.sh` | RDG check 脚本路径 |

## 统一模板变量清单

- `BASE_IMAGE`
- `WORKDIR`
- `APP_SRC`
- `APP_DST`
- `EXPOSE_PORTS`
- `START_CMD`
- `RUNTIME_DEPS_INSTALL`
- `COPY_APP`
- `ENV_BLOCK`
- `NPM_INSTALL_BLOCK`
- `PIP_REQUIREMENTS_BLOCK`

## 平台契约解释（执行时必须牢记）

- 平台 run 命令会显式传 `/start.sh`。
- 因此 `/start.sh` 必须可执行。
- `/start.sh` 必须能启动真实服务。
- `/start.sh` 必须保持容器持续运行。
- `/start.sh` 必须有可观测日志输出。
- `/flag` 默认必须存在且可读（RDG 且 `include_flag_artifact=false` 可放行）。
- `/bin/bash` 必须存在。
- 单服务必须 `exec` 主进程。
- 多服务可后台一个前台一个，但不能空转。

## AI Orchestrated Mode（强制协议）

本技能默认运行在 AI 编排模式，目标是“用户只做 5 项确认，AI 自动完成其余步骤”。

### 总原则

- AI 必须优先执行脚本：`derive_config.py`、`render.py`、`validate.sh`。
- AI 不得要求用户自己执行任何命令。
- AI 不得凭经验直接手写 Dockerfile 取代脚本输出。
- AI 必须把关键默认值的证据（evidence）解释给用户。

### Step 0（AI 自动执行，不询问用户）

白皮书对应：`README.md` -> `6. AI Orchestrated Wizard（5 问确认 + OK 门槛）`

AI 必须先执行：

```bash
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/derive_config.py --project-dir <题目目录> --format json --pretty
```

从输出中提取 ProposedConfig，并生成“配置提案摘要”（仅 5 项）：

1. 技术栈猜测
2. 端口猜测
3. WORKDIR 猜测
4. 启动命令候选（最多 3 个）
5. app_src/app_dst 拷贝路径建议

每项必须附带 evidence（命中文件/规则）。
若输出包含 `config_proposal` 字段，优先直接用于 Step 1 的 YAML 确认块渲染。

### Step 1（仅问 5 个确认问题）

白皮书对应：`README.md` -> `5. 输入契约（challenge.yaml + CONFIG PROPOSAL）`

AI 必须按固定顺序提问，且每题都带默认值：

Q1 技术栈 
默认：`<stack_guess.id>` 
可选：`node/php/python/java/tomcat/lamp/pwn/ai/rdg`

Q2 容器端口 
默认：`<port_guess.ports>` 
格式：单端口或逗号分隔多端口

Q3 工作目录 WORKDIR 
默认：`<workdir_guess.workdir>`

Q4 启动命令 
默认：候选 1 
同时展示候选 2/3 
允许用户直接输入自定义命令

Q5 代码拷贝路径 
默认：`app_src="." -> app_dst=WORKDIR`

固定提问模板（必须按此结构）：

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

请确认以下 5 项（直接回车使用默认值也可以）：
Q1 技术栈 [默认: <stack_guess.id>]：
Q2 容器端口 [默认: <ports>]：
Q3 WORKDIR [默认: <workdir>]：
Q4 启动命令 [默认: <cmd1>; 备选: <cmd2>/<cmd3>]：
Q5 代码拷贝 [默认: <app_src> -> <app_dst>]：
```

Step 1 末尾硬规则（必须执行）：

1. 在提问结束后，AI 必须输出“证据摘要”，最多 5 行，每行只说明 1 条命中依据（例如命中 `package.json`、`app.py`、`ROOT.war`、`requirements.txt` 或 `stacks.yaml` 默认规则）。
2. 证据摘要后，AI 必须输出一个单独的 YAML 配置块，标题固定为 `CONFIG PROPOSAL`，键名固定如下：

```yaml
CONFIG PROPOSAL:
  stack: <node|php|python|java|tomcat|lamp|pwn|ai|rdg>
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
  flag:
    path: "/flag"
    permission: "444"
  rdg:
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
```

3. YAML 块后必须原样输出以下两句话（不得改写）：

“如果以上配置正确，请回复：OK”

“如果需要修改，请直接在上面的 YAML 块里改对应行并发回（不要额外解释），我会按你修改后的配置继续生成与校验。”

交互约束：

- 不允许追加第 6 个问题，除非输入明显冲突且无法继续。
- 每题都要给“为何默认如此”的证据说明（简短）。
- 如果用户输入的启动命令可能只监听 `127.0.0.1`，AI 必须提示改为 `0.0.0.0` 并给出示例。
- 用户若仅回复散乱文本，AI 不得进入生成阶段；必须要求其“回复 OK”或“粘贴修改后的 CONFIG PROPOSAL YAML”。

### Step 2（用户确认后 AI 自动生成）

白皮书对应：`README.md` -> `6. AI Orchestrated Wizard（5 问确认 + OK 门槛）`

AI 自动完成：

进入 Step 2 的门槛（硬规则）：

- 只有当用户回复 `OK`，或返回一段可被解析的 `CONFIG PROPOSAL` YAML 时，才能继续。
- 若用户输入无法解析为配置块，AI 只能提示重发 `OK` 或 YAML，不得开始 render/validate。

AI 自动完成（按顺序）：

1. 用户回复 `OK`：
   - 采用 Step 1 中最后一版 `CONFIG PROPOSAL`。
2. 用户回复 YAML：
   - 先执行 `parse_config_block.py` 从 stdin 解析为 `challenge.yaml`。
3. 执行 `render.py` 生成 `Dockerfile/start.sh/flag(可选)+check 脚手架`。
4. 执行 `validate.sh` 做静态校验。

推荐命令链：

```bash
cat <project_dir>/config-proposal.yaml | python3 src/CloverSec-CTF-Build-Dockerizer/scripts/parse_config_block.py --output <project_dir>/challenge.yaml
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/render.py --config <project_dir>/challenge.yaml --output <project_dir>
bash src/CloverSec-CTF-Build-Dockerizer/scripts/validate.sh <project_dir>/Dockerfile <project_dir>/start.sh <project_dir>/challenge.yaml
```

修复策略：

- 若 validate 出现 ERROR：AI 必须自动修复并重跑 validate，直到 `ERROR=0` 或确认无法自动修复。
- 若仅 WARN：允许继续，但必须解释影响与建议。

### Step 3（交付输出）

白皮书对应：`README.md` -> `7. 手动模式与等价命令链` 与 `15. 发布前验收清单`

AI 必须输出：

- 最终文件清单：`challenge.yaml`、`Dockerfile`、`start.sh`、`flag(可选)`、`check/check.sh(按 rdg.check_enabled 生成)`
- 本地测试命令：`docker build` + `docker run ... /start.sh`
- 平台导入提醒：端口映射、固定 `/start.sh` 启动、动态 flag 依赖 bash

### 低交互失败保护规则

1. 栈侦测置信度 `<0.6`：
   - 仍给默认值
   - 但 Q1 必须强提示“请确认技术栈”

2. 找不到可用入口文件：
   - Q4 强提示“必须确认/填写启动命令”

3. 端口为空：
   - 回退栈默认端口
   - Q2 强提示“请确认端口”

## 手动模式（备用）

当 AI 编排不可用时，允许按传统命令链手动执行：

```bash
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/render.py --config challenge.yaml --output .
bash src/CloverSec-CTF-Build-Dockerizer/scripts/validate.sh Dockerfile start.sh challenge.yaml
docker build -t <image>:latest .
docker run -d -p <host_port>:<container_port> <image>:latest /start.sh
```

## 9 栈最小模板库索引

### Node

适用：

- Node 原生 http
- Express
- Koa
- Fastify

默认：

- 端口 `3000`
- 启动命令 `node server.js`

最小启动命令范式：

- `node server.js`

可选变体：

- `npm run start`
- `pm2-runtime app.js`（可选，不默认）

模板路径：

- `src/CloverSec-CTF-Build-Dockerizer/templates/node/Dockerfile.tpl`
- `src/CloverSec-CTF-Build-Dockerizer/templates/node/start.sh.tpl`
- `src/CloverSec-CTF-Build-Dockerizer/templates/node/README.md`

### PHP (Apache)

适用：

- 传统 PHP 站点
- 轻量 PHP 框架

默认：

- 端口 `80`
- 启动命令 `apache2-foreground`

最小启动命令范式：

- `apache2-foreground`

可选变体：

- php-fpm 分支（可扩展，不默认）

模板路径：

- `src/CloverSec-CTF-Build-Dockerizer/templates/php/Dockerfile.tpl`
- `src/CloverSec-CTF-Build-Dockerizer/templates/php/start.sh.tpl`
- `src/CloverSec-CTF-Build-Dockerizer/templates/php/README.md`

### Python

适用：

- Flask
- FastAPI
- Django
- 自写 HTTP

默认：

- 端口 `5000`
- 启动命令 `python app.py`

最小启动命令范式：

- `python app.py`

可选变体：

- `gunicorn -b 0.0.0.0:5000 app:app`
- `uvicorn app:app --host 0.0.0.0 --port 5000`

模板路径：

- `src/CloverSec-CTF-Build-Dockerizer/templates/python/Dockerfile.tpl`
- `src/CloverSec-CTF-Build-Dockerizer/templates/python/start.sh.tpl`
- `src/CloverSec-CTF-Build-Dockerizer/templates/python/README.md`

### Java (JAR)

适用：

- 已有可运行 `app.jar`

默认：

- 端口 `8080`
- 启动命令 `java -jar app.jar`

最小启动命令范式：

- `java -jar app.jar`

可选变体：

- `java -Xms128m -Xmx256m -jar app.jar`

模板路径：

- `src/CloverSec-CTF-Build-Dockerizer/templates/java/Dockerfile.tpl`
- `src/CloverSec-CTF-Build-Dockerizer/templates/java/start.sh.tpl`
- `src/CloverSec-CTF-Build-Dockerizer/templates/java/README.md`

### Tomcat (WAR)

适用：

- 已有 WAR 包部署

默认：

- 端口 `8080`
- 启动命令 `catalina.sh run`

最小启动命令范式：

- `catalina.sh run`

可选变体：

- 多 WAR 场景可复制整个 webapps 目录

模板路径：

- `src/CloverSec-CTF-Build-Dockerizer/templates/tomcat/Dockerfile.tpl`
- `src/CloverSec-CTF-Build-Dockerizer/templates/tomcat/start.sh.tpl`
- `src/CloverSec-CTF-Build-Dockerizer/templates/tomcat/README.md`

### LAMP

适用：

- 同容器内需要 Apache + PHP + MariaDB

默认：

- 端口 `80`
- 启动命令 `apache2ctl -D FOREGROUND`

最小启动命令范式：

- 后台启动 MariaDB
- 前台 `exec apache2ctl -D FOREGROUND`

可选变体：

- 使用 `MYSQL_INIT_SQL_B64` 注入初始化 SQL
- 可扩展 supervisor（不默认）

模板路径：

- `src/CloverSec-CTF-Build-Dockerizer/templates/lamp/Dockerfile.tpl`
- `src/CloverSec-CTF-Build-Dockerizer/templates/lamp/start.sh.tpl`
- `src/CloverSec-CTF-Build-Dockerizer/templates/lamp/README.md`

### Pwn (xinetd)

适用：

- Jeopardy 模式二进制远程交互题目
- 以 xinetd 托管挑战进程

默认：

- 端口 `10000`
- 启动命令 `/usr/sbin/xinetd -dontfork`

最小启动命令范式：

- `exec /usr/sbin/xinetd -dontfork`

可选变体：

- 在 `start.sh` 启动前将 `/flag` 同步到 `/home/ctf/flag`
- 根据 `ctf.xinetd` 动态调整端口与 server_args

模板路径：

- `src/CloverSec-CTF-Build-Dockerizer/templates/pwn/Dockerfile.tpl`
- `src/CloverSec-CTF-Build-Dockerizer/templates/pwn/start.sh.tpl`
- `src/CloverSec-CTF-Build-Dockerizer/templates/pwn/README.md`

### AI (CPU)

适用：

- CTF AI Web 题目（Flask/FastAPI 等）
- 高核心宿主机下需限制线程的 CPU 推理场景

默认：

- 端口 `5000`
- 启动命令 `gunicorn -w 1 --threads 1 -b 0.0.0.0:5000 app:app`

最小启动命令范式：

- `exec gunicorn -w 1 --threads 1 -b 0.0.0.0:5000 app:app`

可选变体：

- 轻量模式：`ai-basic`（Flask + gunicorn）
- 增强模式：`ai-transformers-basic`（含 transformers 依赖）

模板路径：

- `src/CloverSec-CTF-Build-Dockerizer/templates/ai/Dockerfile.tpl`
- `src/CloverSec-CTF-Build-Dockerizer/templates/ai/start.sh.tpl`
- `src/CloverSec-CTF-Build-Dockerizer/templates/ai/README.md`

## validate 规则速查

### 常见 ERROR

`Dockerfile 未复制 /start.sh`：

- 去 Dockerfile 增加 `COPY start.sh /start.sh`

`Dockerfile 未复制 /flag`：

- 增加 `COPY flag /flag` 或 `RUN touch /flag`

`/start.sh 权限不对`：

- 增加 `RUN chmod 555 /start.sh`

`/flag 权限不对`：

- 增加 `RUN chmod 444 /flag`

`bash 缺失`：

- Debian/Ubuntu 安装 bash
- Alpine 安装 bash

`EXPOSE 缺失`：

- 增加 `EXPOSE <port>`

`单服务没有 exec`：

- 把启动命令改成 `exec <主命令>`

`检测到空转循环`：

- 删除空转命令，改为真实服务前台启动

`tail -f /dev/null 且没有服务`：

- 启动真实服务，不允许只靠 `/dev/null` 保活

### 常见 WARN

`pip install 未带 --no-cache-dir`：

- 在 pip 命令加 `--no-cache-dir`

`npm install 未优先 npm ci`：

- 有 lock 时改为 `npm ci`

`npm 未清理 cache`：

- 安装后 `npm cache clean --force`

`多服务未使用 exec`：

- 确保至少有一个前台主进程并可观测日志

## 输出契约清单（生成后必须满足）

- 产物必须包含 `Dockerfile`、`start.sh`，并在默认模式下包含 `flag`。
- `start.sh` 首行必须是 `#!/bin/bash`。
- `start.sh` 必须包含 `set -euo pipefail`。
- `Dockerfile` 必须有 `EXPOSE`。
- `Dockerfile` 必须把 `start.sh` 放到 `/start.sh`。
- `Dockerfile` 必须把 `flag` 放到 `/flag`（RDG 且 `include_flag_artifact=false` 除外）。
- `Dockerfile` 必须设置 `/start.sh` 可执行。
- `Dockerfile` 必须设置 `/flag` 可读（RDG 且 `include_flag_artifact=false` 除外）。
- 镜像必须有 `/bin/bash`。
- 单服务必须 `exec` 主进程。
- 不能使用空转保活。
- 注释必须是中文并解释设计原因。

## 故障排查剧本

### 剧本 A: render 失败

1. 检查 `challenge.yaml` 是否可解析。
2. 检查 `stack` 是否在 `stacks.yaml` 支持范围内。
3. 检查模板 include 路径是否存在。
4. 检查模板变量是否都可替换。

### 剧本 B: validate 失败

1. 先看 ERROR。
2. 按错误文案改 Dockerfile/start.sh。
3. 重新 render。
4. 重新 validate。
5. 直到 ERROR 为 0。

### 剧本 C: build 失败

1. 看 Docker build 日志中失败层。
2. 检查基础镜像与包管理器匹配。
3. 检查依赖命令是否与镜像发行版一致。

### 剧本 D: run 失败

1. `docker logs` 看启动输出。
2. 检查 `START_CMD` 是否正确。
3. 检查监听地址是否 `0.0.0.0`。
4. 检查端口映射。

### 剧本 E: 运行但访问失败

1. 服务是否只监听 localhost。
2. `EXPOSE` 是否匹配 challenge 端口。
3. `docker run -p` 是否映射正确。

### 剧本 F: 运行但无日志

1. 服务是否写 stdout/stderr。
2. 多服务是否 tail 真实日志文件。
3. 避免仅靠 `/dev/null`。

### 剧本 G: 同步后技能目录不完整

1. 执行 `bash scripts/sync.sh`。
2. 检查目标目录是否包含 `SKILL.md/README.md/data/scripts/templates/examples/docs`。
3. 若目标不可写，改用 `--target-dir`。

## 命令速查

### 渲染

```bash
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/render.py --config challenge.yaml
```

### 校验

```bash
bash src/CloverSec-CTF-Build-Dockerizer/scripts/validate.sh Dockerfile start.sh challenge.yaml
```

### 示例回归

```bash
bash src/CloverSec-CTF-Build-Dockerizer/scripts/validate_examples.sh
```

### 冒烟

```bash
bash src/CloverSec-CTF-Build-Dockerizer/scripts/smoke_test.sh
```

### 清理

```bash
bash src/CloverSec-CTF-Build-Dockerizer/scripts/cleanup_test_containers.sh
```

### 同步

```bash
bash scripts/sync.sh
```

```bash
bash scripts/sync.sh --codex-dir
```

## 对LLM&Agent工具的执行要求

- 优先遵循平台契约。
- 优先生成可运行结果，再追求优化。
- 出现 ERROR 必须自动修复并重试。
- 出现 WARN 必须解释影响。
- 不跳过校验。
- 不用空转手段伪造存活。

## 对维护者的执行要求

- 新增栈时同步更新 data/templates/examples/docs。
- 新增规则时消息必须给修复指引。
- 变更后必须跑回归。
- 发布前必须同步到技能目录并检查完整性。

## 自检清单（交付前）

- `render.py` 能渲染目标目录。
- `validate.sh` 无 ERROR。
- 示例回归通过。
- 关键示例可 build/run。
- docs 链接有效。
- sync 后目录自包含。

## 变更边界

本技能默认不做：

- 业务代码漏洞修复。
- 数据库业务逻辑设计。
- AWD/AWDP 赛制编排。

本技能只处理：

- Jeopardy 模式 Web/Pwn/AI 与 RDG（Docker）题目环境容器入口标准化。
- 平台契约合规。
- 模板化复用与可验证交付。

## 相关文件索引

- `README.md`
- `src/CloverSec-CTF-Build-Dockerizer/data/schema.md`
- `src/CloverSec-CTF-Build-Dockerizer/data/stacks.yaml`
- `src/CloverSec-CTF-Build-Dockerizer/data/validate_rules.yaml`
- `src/CloverSec-CTF-Build-Dockerizer/templates/node/README.md`
- `src/CloverSec-CTF-Build-Dockerizer/templates/php/README.md`
- `src/CloverSec-CTF-Build-Dockerizer/templates/python/README.md`
- `src/CloverSec-CTF-Build-Dockerizer/templates/java/README.md`
- `src/CloverSec-CTF-Build-Dockerizer/templates/tomcat/README.md`
- `src/CloverSec-CTF-Build-Dockerizer/templates/lamp/README.md`
- `src/CloverSec-CTF-Build-Dockerizer/templates/pwn/README.md`
- `src/CloverSec-CTF-Build-Dockerizer/templates/ai/README.md`
- `src/CloverSec-CTF-Build-Dockerizer/templates/rdg/README.md`
- `src/CloverSec-CTF-Build-Dockerizer/docs/platform_contract.md`
- `src/CloverSec-CTF-Build-Dockerizer/docs/stack_cookbook.md`
- `src/CloverSec-CTF-Build-Dockerizer/docs/troubleshooting.md`
- `src/CloverSec-CTF-Build-Dockerizer/docs/beginner_guide.md`

## 附录 A: 单栈最小命令

Node:

```bash
cd src/CloverSec-CTF-Build-Dockerizer/examples/node-basic
python3 ../../scripts/render.py --config challenge.yaml --output .
bash ../../scripts/validate.sh Dockerfile start.sh challenge.yaml
docker build -t ctf-node-basic:latest .
docker run -d -p 3001:3000 ctf-node-basic:latest /start.sh
```

PHP:

```bash
cd src/CloverSec-CTF-Build-Dockerizer/examples/php-apache-basic
python3 ../../scripts/render.py --config challenge.yaml --output .
bash ../../scripts/validate.sh Dockerfile start.sh challenge.yaml
docker build -t ctf-php-apache-basic:latest .
docker run -d -p 8081:80 ctf-php-apache-basic:latest /start.sh
```

Python:

```bash
cd src/CloverSec-CTF-Build-Dockerizer/examples/python-flask-basic
python3 ../../scripts/render.py --config challenge.yaml --output .
bash ../../scripts/validate.sh Dockerfile start.sh challenge.yaml
docker build -t ctf-python-flask-basic:latest .
docker run -d -p 5001:5000 ctf-python-flask-basic:latest /start.sh
```

Java:

```bash
cd src/CloverSec-CTF-Build-Dockerizer/examples/java-jar-basic
python3 ../../scripts/render.py --config challenge.yaml --output .
bash ../../scripts/validate.sh Dockerfile start.sh challenge.yaml
docker build -t ctf-java-jar-basic:latest .
docker run -d -p 8082:8080 ctf-java-jar-basic:latest /start.sh
```

Tomcat:

```bash
cd src/CloverSec-CTF-Build-Dockerizer/examples/tomcat-war-basic
python3 ../../scripts/render.py --config challenge.yaml --output .
bash ../../scripts/validate.sh Dockerfile start.sh challenge.yaml
docker build -t ctf-tomcat-war-basic:latest .
docker run -d -p 8083:8080 ctf-tomcat-war-basic:latest /start.sh
```

LAMP:

```bash
cd src/CloverSec-CTF-Build-Dockerizer/examples/lamp-basic
python3 ../../scripts/render.py --config challenge.yaml --output .
bash ../../scripts/validate.sh Dockerfile start.sh challenge.yaml
docker build -t ctf-lamp-basic:latest .
docker run -d -p 8084:80 ctf-lamp-basic:latest /start.sh
```

Pwn:

```bash
cd src/CloverSec-CTF-Build-Dockerizer/examples/pwn-basic
python3 ../../scripts/render.py --config challenge.yaml --output .
bash ../../scripts/validate.sh Dockerfile start.sh challenge.yaml
docker build -t ctf-pwn-basic:latest .
docker run -d -p 10001:10000 ctf-pwn-basic:latest /start.sh
```

AI:

```bash
cd src/CloverSec-CTF-Build-Dockerizer/examples/ai-basic
python3 ../../scripts/render.py --config challenge.yaml --output .
bash ../../scripts/validate.sh Dockerfile start.sh challenge.yaml
docker build -t ctf-ai-basic:latest .
docker run -d -p 5002:5000 ctf-ai-basic:latest /start.sh
```

## 附录 B: 回归命令

```bash
bash src/CloverSec-CTF-Build-Dockerizer/scripts/validate_examples.sh
```

```bash
bash src/CloverSec-CTF-Build-Dockerizer/scripts/smoke_test.sh
```

```bash
bash src/CloverSec-CTF-Build-Dockerizer/scripts/cleanup_test_containers.sh
```
