# CloverSec-CTF-Build-Dockerizer：Skill工程指南

`CloverSec-CTF-Build-Dockerizer` 是四叶草安全-创研中心竞赛专用题目容器构建技能，用于把 CTF 题目工程转换为符合平台约束的可交付容器入口，产物固定为 `Dockerfile + start.sh + flag`。本文档是对外发布主文档，面向双受众：

- 使用者：需要快速生成题目运行环境。
- 维护者：需要扩展模板、规则、回归与分发流程。

版权所有@四叶草安全-创研中心
VERSION：v1.2.2
Date：2026-2-24

## 目录

1. 项目定位与适用边界
2. 平台硬约束与设计原因
3. 架构总览（source-of-truth + sync + 双技能目录）
4. 能力盘点与证据矩阵
5. 输入契约（challenge.yaml + CONFIG PROPOSAL）
6. AI Orchestrated Wizard（5 问确认 + OK 门槛）
7. 手动模式与等价命令链
8. 八栈能力对照（Node/PHP/Python/Java/Tomcat/LAMP/Pwn/AI）
9. 模板系统（snippets/include/变量契约）
10. 校验系统（硬规则 + 可配置规则 + 分级）
11. 示例体系（新旧目录策略与最小运行样例）
12. 运维与回归（validate/smoke/cleanup）
13. 分发与发布（sync、zip、目录自包含）
14. 风险与故障排查
15. 发布前验收清单（可复制命令）
16. 版本更新记录
17. 术语表
18. README/SKILL 严格审计清单（P0/P1/P2）

## 1. 项目定位与适用边界

### 1.1 项目定位

- 目标：生成可直接构建运行且满足平台规则的题目容器入口。
- 优先级：平台兼容性 > 可观测性 > 可维护性 > 镜像体积。
- 设计哲学：脚本优先、模板复用、规则显式、可回归验证。

### 1.2 适用边界

适用：
- CTF Jeopardy 题目容器化交付。
- 8 类技术栈：`node/php/python/java/tomcat/lamp/pwn/ai`。
- 需要动态 flag 注入兼容。

不适用：
- 完整业务编排平台（如复杂 K8s 多服务网格）。
- 对外生产级服务治理（灰度、观测平台、自动扩缩容）。
- AWD/AWDP 赛制编排与攻防流量治理。

### 1.3 发布边界

- `src/CloverSec-CTF-Build-Dockerizer/` 是唯一真源。
- `.claude/skills/CloverSec-CTF-Build-Dockerizer/` 与 `.codex/skills/CloverSec-CTF-Build-Dockerizer/` 是同步生成态目录。
- `internal/` 下资料仅供内部参考，不进入公开发布包。

## 2. 平台硬约束与设计原因

平台硬约束（必须满足）：

1. 启动方式固定：`docker run -d -p host:container <image>:latest /start.sh`
2. 镜像必须包含 `/start.sh` 且可执行。
3. 镜像必须包含 `/flag` 且可读（平台启动后动态写入）。
4. 镜像必须包含 `/bin/bash`（平台调用 `/bin/bash /changeflag.sh`）。
5. Dockerfile 必须包含 `EXPOSE`。
6. 禁止空转保活（`sleep infinity`、`while true; do sleep ...`）。
7. 单服务必须 `exec` 主进程作为 PID1。
8. 必须有可观测日志输出。

设计原因详见：`src/CloverSec-CTF-Build-Dockerizer/docs/platform_contract.md`

## 3. 架构总览（source-of-truth + sync + 双技能目录）

### 3.1 核心目录

- `src/CloverSec-CTF-Build-Dockerizer/`
  - 真源：模板、脚本、规则、示例、SKILL 协议、维护文档。
- `scripts/sync.sh`
  - 把真源同步到技能目录。
- `.claude/skills/CloverSec-CTF-Build-Dockerizer/`
  - Claude 安装态技能目录（生成态）。
- `.codex/skills/CloverSec-CTF-Build-Dockerizer/`
  - Codex 安装态技能目录（生成态）。

### 3.2 执行流水线

1. 侦测/提案：`derive_config.py`
2. 确认块转配置：`parse_config_block.py`
3. 生成产物：`render.py`
4. 静态校验：`validate.sh`
5. 示例回归：`validate_examples.sh`
6. 构建运行冒烟：`smoke_test.sh`
7. 清理测试资源：`cleanup_test_containers.sh`

## 4. 能力盘点与证据矩阵

| 能力 | 作用 | 入口 | 证据文件 |
|---|---|---|---|
| 栈自动侦测 | 自动识别 node/php/python/java/tomcat/lamp/pwn/ai | `python3 src/CloverSec-CTF-Build-Dockerizer/scripts/detect_stack.py --dir .` | `src/CloverSec-CTF-Build-Dockerizer/data/stacks.yaml` |
| 配置提案 | 输出机器可读 ProposedConfig（含 evidence） | `python3 src/CloverSec-CTF-Build-Dockerizer/scripts/derive_config.py --project-dir . --format json --pretty` | `src/CloverSec-CTF-Build-Dockerizer/scripts/derive_config.py` |
| 配置确认块解析 | 解析 `CONFIG PROPOSAL` YAML -> `challenge.yaml` | `cat config.yaml \| python3 src/CloverSec-CTF-Build-Dockerizer/scripts/parse_config_block.py --output challenge.yaml` | `src/CloverSec-CTF-Build-Dockerizer/scripts/parse_config_block.py` |
| 模板渲染 | 生成 Dockerfile/start.sh/flag | `python3 src/CloverSec-CTF-Build-Dockerizer/scripts/render.py --config challenge.yaml --output .` | `src/CloverSec-CTF-Build-Dockerizer/scripts/render.py` |
| include 模板片段 | 减少八栈重复逻辑 | 渲染时自动内联 `{{> snippets/... }}` | `src/CloverSec-CTF-Build-Dockerizer/scripts/utils.py` |
| 静态规则校验 | 平台硬规则 + 可配置规则 | `bash src/CloverSec-CTF-Build-Dockerizer/scripts/validate.sh Dockerfile start.sh [challenge.yaml]` | `src/CloverSec-CTF-Build-Dockerizer/scripts/validate.sh` + `src/CloverSec-CTF-Build-Dockerizer/data/validate_rules.yaml` |
| 示例回归 | 批量校验 examples | `bash src/CloverSec-CTF-Build-Dockerizer/scripts/validate_examples.sh` | `src/CloverSec-CTF-Build-Dockerizer/examples/` |
| 冒烟回归 | render/validate/build/run 生存性检查 | `bash src/CloverSec-CTF-Build-Dockerizer/scripts/smoke_test.sh` | `src/CloverSec-CTF-Build-Dockerizer/scripts/smoke_test.sh` |
| 分发同步 | 真源同步为技能目录 | `bash scripts/sync.sh` | `scripts/sync.sh` |

## 5. 输入契约（challenge.yaml + CONFIG PROPOSAL）

### 5.1 challenge.yaml（标准输入）

完整 schema 见：`src/CloverSec-CTF-Build-Dockerizer/data/schema.md`

关键字段：

- `challenge.stack`
- `challenge.base_image`
- `challenge.workdir`
- `challenge.app_src` / `challenge.app_dst`
- `challenge.expose_ports`
- `challenge.start.mode` / `challenge.start.cmd`
- `challenge.platform.entrypoint`（默认 `/start.sh`）
- `challenge.flag.path`（默认 `/flag`）

### 5.2 CONFIG PROPOSAL（AI 交互确认块）

AI 在 Step 1 末尾必须输出固定 YAML：

```yaml
CONFIG PROPOSAL:
  stack: node
  base_image: node:20-alpine
  workdir: /app
  app_src: .
  app_dst: /app
  expose_ports: [3000]
  start:
    mode: cmd
    cmd: "node server.js"
  platform:
    entrypoint: "/start.sh"
    require_bash: true
  flag:
    path: "/flag"
    permission: "444"
```

用户仅需：
- 回复 `OK`，或
- 修改 YAML 后直接粘贴回传。

## 6. AI Orchestrated Wizard（5 问确认 + OK 门槛）

执行协议详见：`src/CloverSec-CTF-Build-Dockerizer/SKILL.md`。

### 6.1 固定流程

1. AI 自动运行 `derive_config.py`。
2. AI 仅提 5 个确认项（栈/端口/WORKDIR/启动命令/拷贝路径）。
3. AI 输出 `CONFIG PROPOSAL` 块与固定提示语。
4. 仅当用户回复 `OK` 或可解析 YAML，才进入生成阶段。
5. AI 自动执行 `parse_config_block.py -> render.py -> validate.sh`。
6. `ERROR` 必须自动修复重试；`WARN` 需解释影响。

### 6.2 固定提示语

- “如果以上配置正确，请回复：OK”
- “如果需要修改，请直接在上面的 YAML 块里改对应行并发回（不要额外解释），我会按你修改后的配置继续生成与校验。”

## 7. 手动模式与等价命令链

```bash
# 1) 渲染
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/render.py --config challenge.yaml --output .

# 2) 校验
bash src/CloverSec-CTF-Build-Dockerizer/scripts/validate.sh Dockerfile start.sh challenge.yaml

# 3) 构建
docker build -t ctf-web-demo:latest .

# 4) 运行（平台等价）
docker run -d -p 8080:80 ctf-web-demo:latest /start.sh

# 5) 观察日志
docker logs -f <container_id>
```

## 8. 八栈能力对照（Node/PHP/Python/Java/Tomcat/LAMP/Pwn/AI）

| 栈 | 默认端口 | 启动范式 | 推荐基础镜像 | 典型场景 | 关键限制 |
|---|---|---|---|---|---|
| Node | 3000 | `exec node ...` | `node:20-alpine` | 原生 HTTP/Express/Koa | 必须监听 `0.0.0.0` |
| PHP(Apache) | 80 | `exec apache2-foreground` | `php:8.2-apache` | 传统 PHP Web | Apache 前台运行 |
| Python | 5000 | `exec python ...`/`exec gunicorn ...` | `python:3.11-slim` | Flask/FastAPI | 推荐 `--no-cache-dir` |
| Java(JAR) | 8080 | `exec java -jar ...` | `eclipse-temurin:17-jre-jammy` | 提供可运行 jar | 需确保 jar 路径正确 |
| Tomcat(WAR) | 8080 | `exec catalina.sh run` | `tomcat:9.0-jre17-temurin-jammy` | ROOT.war 部署 | APP_DST 建议固定 webapps/ROOT.war |
| LAMP | 80 | 后台 DB + 前台 Apache | `debian:bookworm-slim` | PHP + 本地 DB 题目 | 多服务日志要可观测 |
| Pwn(xinetd) | 10000 | `exec /usr/sbin/xinetd -dontfork` | `debian:bookworm-slim` | 二进制远程交互题目 | 默认 Jeopardy，不覆盖 AWD/AWDP |
| AI(CPU) | 5000 | `exec gunicorn ...` | `python:3.11-slim` | AI Web 题目 | 建议设置线程限制变量 |

每栈模板说明见：`src/CloverSec-CTF-Build-Dockerizer/templates/<stack>/README.md`

## 9. 模板系统（snippets/include/变量契约）

### 9.1 目录

- 栈模板：`src/CloverSec-CTF-Build-Dockerizer/templates/{node,php,python,java,tomcat,lamp,pwn,ai}/`
- 复用片段：`src/CloverSec-CTF-Build-Dockerizer/templates/snippets/`

### 9.2 include 机制

模板支持：`{{> snippets/xxx.tpl }}`，渲染时自动内联。实现见：`src/CloverSec-CTF-Build-Dockerizer/scripts/utils.py`。

### 9.3 关键变量

- `{{BASE_IMAGE}}`
- `{{WORKDIR}}`
- `{{APP_SRC}}` / `{{APP_DST}}`
- `{{EXPOSE_PORTS}}`
- `{{START_CMD}}`
- `{{RUNTIME_DEPS_INSTALL}}`
- `{{NPM_INSTALL_BLOCK}}` / `{{PIP_REQUIREMENTS_BLOCK}}`

## 10. 校验系统（硬规则 + 可配置规则 + 分级）

### 10.1 硬规则（必须）

- `/start.sh` 与 `/flag` 的复制与权限。
- `#!/bin/bash` 与 bash 可用性。
- `EXPOSE` 必需。
- 禁止空转保活。
- 单服务 `exec` PID1。

实现：`src/CloverSec-CTF-Build-Dockerizer/scripts/validate.sh`

### 10.2 可配置规则

规则定义：`src/CloverSec-CTF-Build-Dockerizer/data/validate_rules.yaml`

支持分级：
- `ERROR`：阻断发布
- `WARN`：可继续但需说明
- `INFO`：建议/通过提示

## 11. 示例体系（新旧目录策略与最小运行样例）

### 11.1 目录策略

- 新标准目录：`*-basic`
- 兼容目录：`node/php/python/java/tomcat/lamp`
- 两类目录默认都纳入回归。

### 11.2 最小可运行示例

- `src/CloverSec-CTF-Build-Dockerizer/examples/node-basic`
- `src/CloverSec-CTF-Build-Dockerizer/examples/php-apache-basic`
- `src/CloverSec-CTF-Build-Dockerizer/examples/python-flask-basic`
- `src/CloverSec-CTF-Build-Dockerizer/examples/pwn-basic`
- `src/CloverSec-CTF-Build-Dockerizer/examples/ai-basic`
- `src/CloverSec-CTF-Build-Dockerizer/examples/ai-transformers-basic`

## 12. 运维与回归（validate/smoke/cleanup）

```bash
# 全量静态回归
bash src/CloverSec-CTF-Build-Dockerizer/scripts/validate_examples.sh

# 冒烟回归（含 build/run）
bash src/CloverSec-CTF-Build-Dockerizer/scripts/smoke_test.sh

# 清理测试容器与镜像
bash src/CloverSec-CTF-Build-Dockerizer/scripts/cleanup_test_containers.sh
```

## 13. 分发与发布（sync、zip、目录自包含）

### 13.1 同步

```bash
# 同步到 .claude/skills
bash scripts/sync.sh

# 同步到 .codex/skills（可写时）
bash scripts/sync.sh --codex-dir
```

### 13.2 发布包构建（zip）

```bash
bash scripts/release_build.sh
```

发布脚本会读取根目录 `VERSION`（例如 `v1.2.0`），产物固定为：

- `dist/CloverSec-CTF-Build-Dockerizer-v1.2.0/`
- `dist/CloverSec-CTF-Build-Dockerizer-v1.2.0.zip`

说明：
- zip 为单目录分发，不包含 `.claude/.codex` 双树。
- 技能根目录不包含 `README.md`（避免部分 Agent 工具误识别）。

且显式排除：
- `internal/**`
- `.DS_Store`
- `__pycache__`
- `*.pyc`

## 14. 风险与故障排查

高频风险与剧本详见：`src/CloverSec-CTF-Build-Dockerizer/docs/troubleshooting.md`

重点关注：
- start.sh 不前台导致容器退出
- 仅监听 `127.0.0.1` 导致端口不通
- bash 缺失导致动态 flag 注入失败
- WORKDIR 与 start.sh 不一致
- 尾随 `/dev/null` 造成假活

## 15. 发布前验收清单

```bash
# 1) 公开文档隐私扫描（internal 可忽略）
rg -n --hidden --glob '!.git' --glob '!internal/**' '/[Uu]sers/|yuque\\.com/[A-Za-z0-9_-]+|By\[@' README.md src/ .claude/skills/CloverSec-CTF-Build-Dockerizer/ .codex/skills/CloverSec-CTF-Build-Dockerizer/

# 2) Python 脚本语法
python3 -m py_compile src/CloverSec-CTF-Build-Dockerizer/scripts/*.py

# 3) Shell 脚本语法
find scripts src/CloverSec-CTF-Build-Dockerizer/scripts -name '*.sh' -print0 | xargs -0 -n1 bash -n

# 4) 示例静态回归
bash src/CloverSec-CTF-Build-Dockerizer/scripts/validate_examples.sh

# 5) 同步技能目录
bash scripts/sync.sh

# 6) 构建发布 zip
bash scripts/release_build.sh
```

验收标准：
- 隐私扫描 0 命中（公开范围）。
- `validate_examples.sh` 无 ERROR。
- `dist/` 产物目录与 zip 均包含版本号（来源于 `VERSION`）。
- 发布 zip 为单目录分发，且技能根目录不包含 `README.md`。

## 16. 版本更新记录

### v1.2.2（2026-02-24）

Added:
- 新增文档质量闸门脚本 `scripts/doc_guard.sh`，用于发布前自动检查失效文档引用、禁用文件引用、旧名残留与 Phase 回填完整性。
- `README.md` 的“历史阶段回填（Phase 1-10）”升级为可审计时间表，明确项目起始于 `2026-02-12`，逐阶段记录目标、产出与验收结果。

Fixed:
- 清理公开文档中的失效入口与已下线文档关联，移除不存在路径引用。
- 修复 README 顶部简介病句，统一为发布级表述。

Changed:
- `scripts/release_build.sh` 在发布前检查链路中接入 `doc_guard.sh`，文档检查失败将阻断发布。
- 发布版本升级为 `v1.2.2`，并生成对应版本化分发产物。

Compatibility:
- 不改动 `render.py`、`derive_config.py`、`validate.sh` 核心语义，仅增强文档治理与发布质量闸门。
- 继续仅支持 Jeopardy（Web/Pwn/AI），不支持 AWD/AWDP。

### v1.2.1（2026-02-24）

Added:
- `SKILL.md` frontmatter 描述升级为“技术硬核 + 业务价值”表达，明确该技能是面向 Jeopardy(Web/Pwn/AI) 的智能容器交付引擎。
- `argument-hint` 升级为 8 栈提示（`node/php/python/java/tomcat/lamp/pwn/ai`），避免只展示 node 导致新手误判能力边界。

Changed:
- 发布版本号从 `v1.2.0` 迭代到 `v1.2.1`，并沿用版本号驱动的 dist 命名策略。

Compatibility:
- 不改变 `render.py`、`derive_config.py`、`validate.sh` 核心语义，仅更新文案与版本治理信息。
- Jeopardy 支持边界保持不变，仍不支持 AWD/AWDP。

### v1.2.0（2026-02-24）

Added:
- 发布产物命名新增强约束：目录与 zip 均强制携带版本号，且版本号仅来源于根 `VERSION` 文件。
- 发布前新增 `VERSION` 非空与格式校验（`^vX.Y.Z([a-z0-9.-]+)?$`）。
- 完成技能全量改名为 `CloverSec-CTF-Build-Dockerizer` 并切换真源目录。
- 新增 `pwn` 与 `ai` 两栈，模板、推断、校验、示例、回归链路全部接入。

Fixed:
- 修复 dist 产物命名歧义问题，避免无版本包导致的追溯困难。

Changed:
- `scripts/release_build.sh` 产物结构改为单目录分发：`CloverSec-CTF-Build-Dockerizer-<VERSION>/` 与同名 zip。
- 发布 zip 不再包含 `.claude/.codex` 双树结构。
- 冒烟策略更新：默认强制 run 包含 `pwn-basic` 与 `ai-basic`，`ai-transformers-basic` 默认 build+validate。

Compatibility:
- 不影响 `render.py` 与 `validate.sh` 核心语义；仅调整发布打包命名与结构。
- 安装到 `.claude/.codex` 的同步流程仍通过 `scripts/sync.sh` 保持不变。
- 本版本仅支持 Jeopardy 模式，不支持 AWD/AWDP。

### v1.0.0（2026-02-12）

Added:
- 建立完整 CTF Web 容器化技能链路：`derive_config.py -> parse_config_block.py -> render.py -> validate.sh`。
- 完成 6 栈最小模板库（Node/PHP/Python/Java/Tomcat/LAMP）与 snippets 复用体系。
- 新增 AI Orchestrated 流程与 `CONFIG PROPOSAL` 确认块协议。
- 完成示例回归体系：`validate_examples.sh`、`smoke_test.sh`、`cleanup_test_containers.sh`。
- 建立发布链路：`sync.sh` + `release_build.sh` + zip 分发结构。
- 文档体系完善：白皮书、维护文档、新手指南、故障排查、对外宣传文成稿包。

Fixed:
- 修复 Dockerfile 渲染中 inline include 产生独立 `;` 行导致 `Unknown instruction: ;` 的问题。
- 发布包移除技能根目录 `README.md`，避免部分 Agent 工具误识别；保留 `examples/*/README.md`。
- 新增 Dockerfile 独立分号行校验规则，防止同类问题回归。

Changed:
- 发布包目录契约变更为：技能根仅包含 `SKILL.md/data/scripts/templates/examples/docs`。
- 根 `README.md` 升级为公开版本变更入口，统一记录发布历史。

Compatibility:
- `render.py`/`validate.sh` 主语义保持不变；现有 `challenge.yaml` 配置可继续使用。
- 若本地 Git 未配置用户信息，仓库初始化时允许设置本地占位值（后续可按团队规范覆盖）。

### 历史阶段回填（Phase 1-10）

项目启动锚点：`2026-02-12`

| Phase | 日期 | 目标 | 关键产出 | 验收结果 |
|---|---|---|---|---|
| Phase 1 | 2026-02-12 | 初始化技能工程骨架与 source-of-truth 结构 | 建立 `src/CloverSec-CTF-Build-Dockerizer`、`scripts/sync.sh`、基础目录树 | 结构可同步、语法检查通过 |
| Phase 2 | 2026-02-12 | 定义稳定输入契约与栈识别数据 | `data/stacks.yaml`、`data/schema.md`、基础 examples challenge | 6 栈 schema 可读、示例可解析 |
| Phase 3 | 2026-02-13 | 建立最小可运行模板库 | 6 栈 `Dockerfile.tpl/start.sh.tpl/README.md` + snippets 初版 | 模板可渲染、符合平台硬约束 |
| Phase 4 | 2026-02-13 | 完成渲染链路与自动侦测 | `render.py`、`detect_stack.py`、`utils.py` | Node/Python 示例可生成三件套 |
| Phase 5 | 2026-02-14 | 完成静态校验体系 | `validate.sh`、`validate_examples.sh`、规则分级输出 | `ERROR=>exit 1` 生效，示例回归可执行 |
| Phase 6 | 2026-02-14 | 完成技能协议与同步治理 | `SKILL.md`、`scripts/sync.sh`、发布前标准约束 | 技能目录可自包含，流程可执行 |
| Phase 7 | 2026-02-15 | 产品化加固与回归自动化 | snippets 复用、`smoke_test.sh`、`cleanup_test_containers.sh`、规则可配置化 | 新旧 examples 可批量回归，冒烟链路闭环 |
| Phase 8 | 2026-02-16 ~ 2026-02-18 | 全面补全可运行化与占位清理 | 6 栈模板实装、examples 完整化、文档补齐、禁空转治理 | `render -> validate -> build/run` 路径稳定 |
| Phase 9 | 2026-02-19 | 文档与分发自包含增强 | 根 README 白皮书化、维护文档完善、docs 体系化、同步策略增强 | 新人可仅靠技能目录完成上手 |
| Phase 10 / 10.1 | 2026-02-23 ~ 2026-02-24 | AI Orchestrated Wizard 协议化 | `derive_config.py`、`parse_config_block.py`、`CONFIG PROPOSAL + OK` 门槛 | 用户最少交互完成生成校验，链路稳定 |

## 17. 术语表

- `stack`：技术栈标识（node/php/python/java/tomcat/lamp/pwn/ai）。
- `proposal`：AI 推导出的配置建议（ProposedConfig）。
- `CONFIG PROPOSAL`：Step 1 输出的 YAML 确认块。
- `render`：将配置渲染为 `Dockerfile/start.sh/flag`。
- `validate`：按硬规则与可配置规则做静态校验。
- `smoke`：构建运行层面的最小生存性验证。
- `source-of-truth`：唯一真源目录（`src/CloverSec-CTF-Build-Dockerizer`）。

## 18. README/SKILL 严格审计清单（P0/P1/P2）

### P0（阻断发布）

- [x] 公开文档不含本机绝对路径。
- [x] 公开文档不含个人用户名/个人主页链接。
- [x] README 与 SKILL 对 AI 流程门槛一致（`OK` 或可解析 YAML 才生成）。
- [x] 公开命令链能跨机器使用（相对路径）。

### P1（发布前必须修复）

- [x] README 覆盖从探测到发布全链路。
- [x] README 给出 8 栈对照与限制。
- [x] README 包含发布前可复制验收命令。
- [x] SKILL 与 README 术语统一（stack/config/proposal/render/validate/smoke）。

### P2（后期优化）

- [ ] 根据使用反馈补充更多真实题目案例。
- [ ] 增加离线文档镜像方案（外链图片本地化）。
- [ ] 引入自动化文档一致性 lint（README/SKILL 字段对比）。

---

维护入口：
- 白皮书主文档：`README.md`
- 使用协议：`src/CloverSec-CTF-Build-Dockerizer/SKILL.md`
- 新手上手（安装/触发/场景）：`src/CloverSec-CTF-Build-Dockerizer/docs/beginner_guide.md`
- 平台契约：`src/CloverSec-CTF-Build-Dockerizer/docs/platform_contract.md`
- 栈手册：`src/CloverSec-CTF-Build-Dockerizer/docs/stack_cookbook.md`
- 故障排查：`src/CloverSec-CTF-Build-Dockerizer/docs/troubleshooting.md`
