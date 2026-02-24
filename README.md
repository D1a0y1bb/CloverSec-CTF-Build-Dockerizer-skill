# CloverSec-CTF-Build-Dockerizer

[English](README.en.md)

[![Version](https://img.shields.io/badge/version-v1.2.4-blue)](https://github.com/D1a0y1bb/CloverSec-CTF-Build-Dockerizer-skill/releases)
[![CTF Scope](https://img.shields.io/badge/CTF-Jeopardy-2ea44f)](https://github.com/D1a0y1bb/CloverSec-CTF-Build-Dockerizer-skill)

面向 CTF Jeopardy（Web / Pwn / AI）的题目容器交付构建 Skill。

本项目将题目目录标准化为平台可交付容器产物，并在生成阶段执行规则校验。默认产物为：

- `Dockerfile`
- `start.sh`
- `flag`

## 1. 项目简介与定位

`CloverSec-CTF-Build-Dockerizer` 的目标是让 CTF 题目容器交付流程可重复、可追溯、可审计。

核心价值：

- 降低人工编排导致的运行失败与平台不兼容风险
- 将输入配置、模板渲染、规则校验收敛到统一流程
- 支持多栈题目在同一标准下生成交付件

## 2. 适用范围与非适用范围

适用范围：

- CTF Jeopardy 题目容器化交付
- 栈类型：`node` / `php` / `python` / `java` / `tomcat` / `lamp` / `pwn` / `ai`

非适用范围：

- AWD / AWDP 赛制编排
- 生产环境微服务治理（灰度、网格、自动扩缩容）

## 3. 一键安装

Codex 安装命令：

```bash
npx -y skills add https://github.com/D1a0y1bb/CloverSec-CTF-Build-Dockerizer-skill --skill cloversec-ctf-build-dockerizer --agent codex -y
```

查看可安装 Skill：

```bash
npx -y skills add https://github.com/D1a0y1bb/CloverSec-CTF-Build-Dockerizer-skill --list
```

## 4. 快速开始

### 4.1 AI 编排流程（推荐）

触发示例：

```text
请使用 CloverSec-CTF-Build-Dockerizer 处理当前题目目录。
先自动探测并输出 CONFIG PROPOSAL；我确认 OK 后，再生成 Dockerfile/start.sh/flag 并运行 validate。
```

流程说明：

1. 自动探测项目栈与启动信息（`derive_config.py`）
2. 生成 `CONFIG PROPOSAL` 供确认
3. 用户回复 `OK` 或修改 YAML
4. 执行 `parse_config_block.py -> render.py -> validate.sh`

### 4.2 手动命令链

```bash
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/derive_config.py --project-dir . --format json --pretty
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/render.py --config challenge.yaml --output .
bash src/CloverSec-CTF-Build-Dockerizer/scripts/validate.sh Dockerfile start.sh challenge.yaml
docker build -t ctf-demo:latest .
docker run -d -p 8080:80 ctf-demo:latest /start.sh
```

## 5. 平台硬约束

交付前必须满足：

1. 平台固定以 `/start.sh` 启动
2. 镜像根目录必须存在 `/flag` 且可读
3. 镜像必须包含 `/bin/bash`
4. Dockerfile 必须包含 `EXPOSE`
5. 禁止空转保活（如 `sleep infinity`）
6. 单服务需以前台 `exec` 方式运行

详细规则见：[platform_contract.md](src/CloverSec-CTF-Build-Dockerizer/docs/platform_contract.md)

## 6. 支持栈矩阵

| Stack | 默认端口 | 启动示例 |
|---|---:|---|
| node | 3000 | `exec node server.js` |
| php | 80 | `exec apache2-foreground` |
| python | 5000 | `exec python app.py` / `exec gunicorn ...` |
| java | 8080 | `exec java -jar app.jar` |
| tomcat | 8080 | `exec catalina.sh run` |
| lamp | 80 | 数据库后台 + Apache 前台 |
| pwn | 10000 | `exec /usr/sbin/xinetd -dontfork` |
| ai | 5000 | `exec gunicorn ...` |

## 7. 仓库结构

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
│   ├── release_build.sh
│   └── publish_release.sh
├── CHANGELOG.md
└── VERSION
```

文档入口：

- 使用协议：[SKILL.md](src/CloverSec-CTF-Build-Dockerizer/SKILL.md)
- 新手指南：[beginner_guide.md](src/CloverSec-CTF-Build-Dockerizer/docs/beginner_guide.md)
- 栈手册：[stack_cookbook.md](src/CloverSec-CTF-Build-Dockerizer/docs/stack_cookbook.md)
- 故障排查：[troubleshooting.md](src/CloverSec-CTF-Build-Dockerizer/docs/troubleshooting.md)

## 8. 发布流程

### 8.1 标准检查与打包

```bash
bash scripts/release_build.sh
```

执行后产物：

- `dist/CloverSec-CTF-Build-Dockerizer-vX.Y.Z/`
- `dist/CloverSec-CTF-Build-Dockerizer-vX.Y.Z.zip`

### 8.2 一键发布（推荐）

```bash
bash scripts/publish_release.sh --version v1.2.4
```

如需从私有源码目录同步后发布：

```bash
bash scripts/publish_release.sh --source-dir /path/to/CloverSec-CTF-Build-Dockerizer --version v1.2.4
```

## 9. 版本与更新记录

- 当前版本：`v1.2.4`
- 变更历史见：[CHANGELOG.md](CHANGELOG.md)
- Release 页面：<https://github.com/D1a0y1bb/CloverSec-CTF-Build-Dockerizer-skill/releases>

## 10. 安全边界与敏感数据策略

- 仓库不包含 `internal/` 私有资料
- 禁止提交真实生产密钥与业务敏感数据
- 示例 `flag` 仅用于流程验证
- 发布前应运行文档与规则检查，避免泄漏路径与隐私信息

## 11. FAQ

### Q1: `npx skills add` 是否依赖 GitHub Release 附件？
不依赖。`npx skills add` 默认从仓库内容安装，Release 附件用于版本化下载与归档。

### Q2: 为什么要求 `/start.sh`、`/flag`、`/bin/bash`？
这是平台运行契约，缺失会导致启动失败或动态 flag 注入失败。

### Q3: 我只改了文档，需要发版吗？
建议发版。文档与安装说明变更同样影响外部使用者，应保持版本可追溯。

### Q4: `internal` 目录为什么不保留在仓库中？
`internal` 常包含内部资料或敏感样本，不适合公开仓库，应做本地归档。

## 12. 维护与贡献说明

建议 PR 提交前执行：

```bash
bash scripts/release_build.sh
npx -y skills add . --list
```

推荐提交范围：

- 模板与规则改进
- 示例补全与文档纠错
- 发布流程和可靠性增强

维护团队：四叶草安全-创研中心
