# CloverSec-CTF-Build-Dockerizer

[![Version](https://img.shields.io/badge/version-v1.2.3-blue)](https://github.com/D1a0y1bb/CloverSec-CTF-Build-Dockerizer-skill/releases)
[![Scope](https://img.shields.io/badge/CTF-Jeopardy-2ea44f)](https://github.com/D1a0y1bb/CloverSec-CTF-Build-Dockerizer-skill)

面向 CTF Jeopardy（Web / Pwn / AI）的题目容器构建 Skill。

该项目用于将题目目录标准化为平台可交付容器产物，并自动执行规则校验，固定产物为：

- `Dockerfile`
- `start.sh`
- `flag`

## 中文说明（主文）

### 1. 项目简介

`CloverSec-CTF-Build-Dockerizer` 聚焦于题目容器交付标准化。
目标是在不牺牲可维护性的前提下，降低手工编排错误，保证题目镜像满足平台运行契约。

### 2. 适用范围

适用：

- CTF Jeopardy 题目容器化交付
- 技术栈：`node` / `php` / `python` / `java` / `tomcat` / `lamp` / `pwn` / `ai`

不适用：

- AWD / AWDP 赛制编排
- 生产级微服务治理与编排（K8s Mesh、灰度策略等）

### 3. 一键安装（Codex）

```bash
npx -y skills add https://github.com/D1a0y1bb/CloverSec-CTF-Build-Dockerizer-skill --skill cloversec-ctf-build-dockerizer --agent codex -y
```

查看仓库内可安装 Skill：

```bash
npx -y skills add https://github.com/D1a0y1bb/CloverSec-CTF-Build-Dockerizer-skill --list
```

### 4. 使用方式

触发示例：

```text
请使用 CloverSec-CTF-Build-Dockerizer 处理当前题目目录。
先自动探测并输出 CONFIG PROPOSAL；我确认 OK 后，再生成 Dockerfile/start.sh/flag 并运行 validate。
```

默认工作流：

1. `derive_config.py` 自动探测并生成提案
2. 输出 `CONFIG PROPOSAL` 供确认
3. 用户回复 `OK` 或修改 YAML
4. `parse_config_block.py -> render.py -> validate.sh`

手动命令链：

```bash
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/derive_config.py --project-dir . --format json --pretty
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/render.py --config challenge.yaml --output .
bash src/CloverSec-CTF-Build-Dockerizer/scripts/validate.sh Dockerfile start.sh challenge.yaml
docker build -t ctf-demo:latest .
docker run -d -p 8080:80 ctf-demo:latest /start.sh
```

### 5. 平台交付约束

交付前必须满足：

1. 平台固定以 `/start.sh` 启动容器
2. 镜像根目录必须包含 `/flag` 且可读
3. 镜像必须包含 `/bin/bash`
4. Dockerfile 必须包含 `EXPOSE`
5. 禁止空转保活（例如 `sleep infinity`）
6. 单服务需以前台 `exec` 方式运行

详见：[platform_contract.md](src/CloverSec-CTF-Build-Dockerizer/docs/platform_contract.md)

### 6. 支持栈

| Stack | 默认端口 | 启动模式（示例） |
|---|---:|---|
| node | 3000 | `exec node server.js` |
| php | 80 | `exec apache2-foreground` |
| python | 5000 | `exec python app.py` / `exec gunicorn ...` |
| java | 8080 | `exec java -jar app.jar` |
| tomcat | 8080 | `exec catalina.sh run` |
| lamp | 80 | 数据库后台 + Apache 前台 |
| pwn | 10000 | `exec /usr/sbin/xinetd -dontfork` |
| ai | 5000 | `exec gunicorn ...` |

### 7. 仓库结构

```text
.
├── src/CloverSec-CTF-Build-Dockerizer/
│   ├── SKILL.md
│   ├── data/
│   ├── templates/
│   ├── scripts/
│   ├── examples/
│   └── docs/
├── scripts/
│   ├── sync.sh
│   ├── doc_guard.sh
│   └── release_build.sh
├── CHANGELOG.md
└── VERSION
```

### 8. 文档索引

- 使用协议：[SKILL.md](src/CloverSec-CTF-Build-Dockerizer/SKILL.md)
- 新手指南：[beginner_guide.md](src/CloverSec-CTF-Build-Dockerizer/docs/beginner_guide.md)
- 栈手册：[stack_cookbook.md](src/CloverSec-CTF-Build-Dockerizer/docs/stack_cookbook.md)
- 故障排查：[troubleshooting.md](src/CloverSec-CTF-Build-Dockerizer/docs/troubleshooting.md)

### 9. 更新记录

详细记录见：[CHANGELOG.md](CHANGELOG.md)

最近版本：

- `v1.2.3`（2026-02-24）：README 正式化重构，新增中英双语说明，新增 `CHANGELOG.md`，补齐 GitHub Release 入口。
- `v1.2.2`（2026-02-24）：文档治理强化，接入 `doc_guard.sh` 发布闸门。
- `v1.2.1`（2026-02-24）：`SKILL.md` frontmatter 与 argument-hint 规范升级。
- `v1.2.0`（2026-02-24）：统一命名为 `CloverSec-CTF-Build-Dockerizer`，扩展 `pwn` 与 `ai` 栈。

Release 页面：

- <https://github.com/D1a0y1bb/CloverSec-CTF-Build-Dockerizer-skill/releases>

### 10. 安全与边界

- 公开仓库不包含 `internal/` 私有资料。
- 禁止提交真实生产密钥、业务敏感数据或比赛敏感附件。
- 示例中的 `flag` 仅用于流程验证。

### 11. 维护团队

四叶草安全-创研中心

---

## English Summary (Brief)

`CloverSec-CTF-Build-Dockerizer` is a delivery-focused skill for CTF Jeopardy challenges (Web/Pwn/AI).
It converts challenge projects into platform-compliant container deliverables (`Dockerfile`, `start.sh`, `flag`) and validates them against strict rules.

### Install (Codex)

```bash
npx -y skills add https://github.com/D1a0y1bb/CloverSec-CTF-Build-Dockerizer-skill --skill cloversec-ctf-build-dockerizer --agent codex -y
```

### Typical Flow

1. Auto-detect project stack and runtime hints
2. Generate `CONFIG PROPOSAL`
3. Confirm with `OK` (or edit YAML)
4. Render and validate deliverables

### Supported Stacks

`node`, `php`, `python`, `java`, `tomcat`, `lamp`, `pwn`, `ai`

### Important Constraints

- Container must start via `/start.sh`
- `/flag` must exist and be readable
- `/bin/bash` must be available
- `EXPOSE` is required
- No idle-keepalive patterns (e.g., `sleep infinity`)

For full details, see [SKILL.md](src/CloverSec-CTF-Build-Dockerizer/SKILL.md) and [CHANGELOG.md](CHANGELOG.md).
