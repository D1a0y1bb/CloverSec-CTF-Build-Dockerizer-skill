# CloverSec-CTF-Build-Dockerizer

[English](README.en.md)

[![Version](https://img.shields.io/badge/version-v1.2.4-blue)](https://github.com/D1a0y1bb/CloverSec-CTF-Build-Dockerizer-skill/releases)
[![Scope](https://img.shields.io/badge/CTF-Jeopardy-2ea44f)](https://github.com/D1a0y1bb/CloverSec-CTF-Build-Dockerizer-skill)
[![Stacks](https://img.shields.io/badge/stacks-8-orange)](https://github.com/D1a0y1bb/CloverSec-CTF-Build-Dockerizer-skill)
[![Release Asset](https://img.shields.io/badge/release-zip-success)](https://github.com/D1a0y1bb/CloverSec-CTF-Build-Dockerizer-skill/releases/tag/v1.2.4)

面向 CTF Jeopardy（Web / Pwn / AI）的容器交付构建 Skill。它将题目目录标准化为平台可运行交付件，并通过规则校验保证质量一致性。

## What's New in v1.2.4

- 新增独立双语文档：`README.md`（中文）与 `README.en.md`（英文）。
- 新增 `Build_test` 真实构建样例（Node / Python 两题）。
- 发布流程统一为 `release_build.sh` + `publish_release.sh`。

<details>
<summary><b>v1.2.4 重点交付</b></summary>

- 标准化三件套输出：`Dockerfile` / `start.sh` / `flag`
- 平台契约校验：`/start.sh`、`/flag`、`/bin/bash`、`EXPOSE`
- 一键安装与一键发布流程可复用

</details>

## 核心能力矩阵

| 能力 | 入口脚本 | 作用 | 输出/结果 |
|---|---|---|---|
| 自动探测 | `derive_config.py` | 识别栈、端口、启动命令候选 | `CONFIG PROPOSAL` 输入依据 |
| 配置解析 | `parse_config_block.py` | 把确认块转为 `challenge.yaml` | 标准化配置 |
| 渲染生成 | `render.py` | 生成 Docker 交付文件 | `Dockerfile` / `start.sh` / `flag` |
| 静态校验 | `validate.sh` | 校验平台硬约束与规则 | ERROR/WARN/INFO |
| 样例回归 | `validate_examples.sh` | 批量验证示例目录 | 回归通过/失败清单 |
| 打包发布 | `release_build.sh` | 生成版本目录和 zip | `dist/...-vX.Y.Z.zip` |
| 一键发布 | `publish_release.sh` | commit/tag/release/上传资产 | GitHub Release 可下载包 |

## 一键安装

```bash
npx -y skills add https://github.com/D1a0y1bb/CloverSec-CTF-Build-Dockerizer-skill --skill cloversec-ctf-build-dockerizer --agent codex -y
```

校验仓库可安装性：

```bash
npx -y skills add https://github.com/D1a0y1bb/CloverSec-CTF-Build-Dockerizer-skill --list
```

## 快速开始

### AI 编排流程（推荐）

```text
请使用 CloverSec-CTF-Build-Dockerizer 处理当前题目目录。
先自动探测并输出 CONFIG PROPOSAL；我确认 OK 后，再生成 Dockerfile/start.sh/flag 并运行 validate。
```

标准步骤：

1. 自动探测（`derive_config.py`）
2. 输出并确认 `CONFIG PROPOSAL`
3. 回复 `OK` 或修改 YAML
4. 渲染并校验（`parse -> render -> validate`）

### 手动命令链

```bash
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/derive_config.py --project-dir . --format json --pretty
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/render.py --config challenge.yaml --output .
bash src/CloverSec-CTF-Build-Dockerizer/scripts/validate.sh Dockerfile start.sh challenge.yaml
```

## Build_test 真实样例

`Build_test` 目录包含 2 个由本 Skill 生成与校验的题目案例：

| Case Name | Stack | Exposed Port | Start Command | Core Files |
|---|---|---:|---|---|
| `CTF-NodeJs RCE-Test1` | `node` | `3000` | `node app.js` | `challenge.yaml` / `Dockerfile` / `start.sh` / `app.js` |
| `CTF-Python沙箱逃逸-Test2` | `python` | `5000` | `python app.py` | `challenge.yaml` / `Dockerfile` / `start.sh` / `src/app.py` |

示例验证命令：

```bash
# Node 例子
cd "Build_test/CTF-NodeJs RCE-Test1"
bash ../../src/CloverSec-CTF-Build-Dockerizer/scripts/validate.sh Dockerfile start.sh challenge.yaml

# Python 例子
cd "../CTF-Python沙箱逃逸-Test2"
bash ../../src/CloverSec-CTF-Build-Dockerizer/scripts/validate.sh Dockerfile start.sh challenge.yaml
```

示例构建与运行：

```bash
# Node
cd "Build_test/CTF-NodeJs RCE-Test1"
docker build -t ctf-node-rce:latest .
docker run -d -p 13000:3000 ctf-node-rce:latest /start.sh

# Python
cd "../CTF-Python沙箱逃逸-Test2"
docker build -t ctf-python-sandbox:latest .
docker run -d -p 15000:5000 ctf-python-sandbox:latest /start.sh
```

<details>
<summary><b>Build_test 提交策略说明</b></summary>

- 保留业务样例文件用于复现实战场景。
- 移除元数据文件（嵌套 `.git` 与 `.DS_Store`）。
- 不影响 `npx skills add` 的技能识别逻辑。

</details>

## 平台硬约束

交付前必须满足：

1. 平台固定以 `/start.sh` 启动
2. 镜像根目录存在 `/flag` 且可读
3. 镜像内包含 `/bin/bash`
4. Dockerfile 包含 `EXPOSE`
5. 禁止空转保活（如 `sleep infinity`）
6. 单服务使用前台 `exec` 作为主进程

详细契约：[platform_contract.md](src/CloverSec-CTF-Build-Dockerizer/docs/platform_contract.md)

## 支持栈

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

## 仓库结构

```text
.
├── Build_test/
│   ├── CTF-NodeJs RCE-Test1/
│   └── CTF-Python沙箱逃逸-Test2/
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

## 发布流程

```bash
# 标准打包
bash scripts/release_build.sh

# 一键发布（commit/tag/release/asset）
bash scripts/publish_release.sh --version v1.2.4
```

## FAQ

### Q1: `Build_test` 的用途是什么？
用于展示本 Skill 在真实题目目录上的生成效果与可复现流程。

### Q2: `npx skills add` 是否依赖 GitHub Release 资产？
不依赖。`npx skills add` 默认按仓库内容安装，Release 资产用于版本下载归档。

### Q3: 为什么必须满足 `/start.sh`、`/flag`、`/bin/bash`？
这是平台运行契约，缺失会导致启动失败或动态 flag 注入失败。

## 维护与贡献

建议在提交前至少执行：

```bash
npx -y skills add . --list
bash scripts/release_build.sh --skip-checks
```

维护团队：四叶草安全-网络安全人才培养与创新研究中心
