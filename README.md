# CloverSec-CTF-Build-Dockerizer

面向 CTF Jeopardy（Web / Pwn / AI）的题目容器构建 Skill。

该 Skill 用于把题目目录转换为平台可交付产物，并自动执行规则校验：

- `Dockerfile`
- `start.sh`
- `flag`

## 项目定位

`CloverSec-CTF-Build-Dockerizer` 聚焦“题目容器交付标准化”。
核心目标是降低人工编排误差，确保产物满足平台运行契约。

适用范围：

- CTF Jeopardy 题目容器化交付
- 技术栈：`node` / `php` / `python` / `java` / `tomcat` / `lamp` / `pwn` / `ai`

不适用范围：

- AWD / AWDP 赛制编排
- 通用生产级微服务编排（K8s Mesh、灰度治理等）

## 一键安装（Codex）

```bash
npx -y skills add https://github.com/D1a0y1bb/CloverSec-CTF-Build-Dockerizer-skill --skill cloversec-ctf-build-dockerizer --agent codex -y
```

可先查看仓库内可安装技能：

```bash
npx -y skills add https://github.com/D1a0y1bb/CloverSec-CTF-Build-Dockerizer-skill --list
```

安装后建议重启 Agent 进程，确保新 Skill 被加载。

## 对话触发示例

```text
请使用 CloverSec-CTF-Build-Dockerizer 处理当前题目目录。
先做自动探测并输出 CONFIG PROPOSAL；我确认 OK 后，再生成 Dockerfile/start.sh/flag 并运行 validate。
```

默认工作流：

1. `derive_config.py` 自动探测并生成提案
2. 输出 `CONFIG PROPOSAL` 供用户确认
3. 用户回复 `OK` 或修改 YAML
4. `parse_config_block.py -> render.py -> validate.sh`

## 手动命令链（本地）

```bash
# 1) 自动提案
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/derive_config.py --project-dir . --format json --pretty

# 2) 渲染产物
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/render.py --config challenge.yaml --output .

# 3) 静态校验
bash src/CloverSec-CTF-Build-Dockerizer/scripts/validate.sh Dockerfile start.sh challenge.yaml

# 4) 本地构建与运行（平台等价）
docker build -t ctf-demo:latest .
docker run -d -p 8080:80 ctf-demo:latest /start.sh
```

## 平台硬约束

以下约束是交付前必须满足的最低标准：

1. 平台固定以 `/start.sh` 启动容器
2. 镜像根目录必须包含 `/flag` 且可读
3. 镜像必须包含 `/bin/bash`
4. Dockerfile 必须包含 `EXPOSE`
5. 禁止空转保活（如 `sleep infinity`）
6. 单服务进程需以前台 `exec` 方式运行

详细说明见：[platform_contract.md](src/CloverSec-CTF-Build-Dockerizer/docs/platform_contract.md)

## 支持栈一览

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

## 仓库结构

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
└── VERSION
```

关键文档：

- 使用协议：[SKILL.md](src/CloverSec-CTF-Build-Dockerizer/SKILL.md)
- 新手指南：[beginner_guide.md](src/CloverSec-CTF-Build-Dockerizer/docs/beginner_guide.md)
- 故障排查：[troubleshooting.md](src/CloverSec-CTF-Build-Dockerizer/docs/troubleshooting.md)
- 栈手册：[stack_cookbook.md](src/CloverSec-CTF-Build-Dockerizer/docs/stack_cookbook.md)

## 发布与版本

版本号由根目录 `VERSION` 文件管理。

发布前建议执行：

```bash
bash scripts/doc_guard.sh
bash src/CloverSec-CTF-Build-Dockerizer/scripts/validate_examples.sh
bash scripts/release_build.sh
```

## 安全与数据边界

- 本公开仓库不包含 `internal/` 私有资料。
- 请勿提交真实生产密钥、真实业务数据或比赛敏感文件。
- 示例中的 `flag` 仅用于流程验证。

## 贡献说明

欢迎通过 Issue / PR 提交：

- 模板优化
- 新栈规则改进
- 文档纠错与示例补全

提交前请至少通过 `validate_examples.sh`。

## 维护方

四叶草安全-创研中心
