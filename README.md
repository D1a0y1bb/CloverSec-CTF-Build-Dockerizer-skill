# CloverSec-CTF-Build-Dockerizer

<p align="center">
  <a href="README.md"><strong>简体中文（默认）</strong></a>
  <span> · </span>
  <a href="README.en.md"><strong>English</strong></a>
  <span> · </span>
  <a href="README.ja.md"><strong>日本語</strong></a>
  <span> · </span>
  <a href="README.zh-CN.md"><strong>中文兼容入口</strong></a>
</p>

<p align="center">
  <img src="docs/assets/readme/CloverSec-CTF-Build-Dockerizer-skill.svg" alt="CloverSec-CTF-Build-Dockerizer-skill" width="920" />
</p>

<p align="center">
  <a href="https://github.com/D1a0y1bb/CloverSec-CTF-Build-Dockerizer-skill/releases"><img src="https://img.shields.io/badge/version-v2.0.2-2563eb?style=for-the-badge" alt="Version" /></a>
  <a href="https://github.com/D1a0y1bb/CloverSec-CTF-Build-Dockerizer-skill"><img src="https://img.shields.io/badge/stacks-11-f59e0b?style=for-the-badge" alt="Stacks" /></a>
  <a href="https://github.com/D1a0y1bb/CloverSec-CTF-Build-Dockerizer-skill"><img src="https://img.shields.io/badge/profiles-jeopardy%2Frdg%2Fawd%2Fawdp%2Fsecops-16a34a?style=for-the-badge" alt="Profiles" /></a>
  <a href="https://github.com/D1a0y1bb/CloverSec-CTF-Build-Dockerizer-skill/releases/tag/v2.0.2"><img src="https://img.shields.io/badge/release-zip%2Bsbom%2Bdeps-10b981?style=for-the-badge" alt="Release Asset" /></a>
</p>

<p align="center"><code><strong>VERSION</strong>: v2.0.2</code></p>

四叶草安全-创研中心竞赛专用题目容器构建 Skill。它的目标不是“再多一个脚本”，而是把 CTF 题目环境交付这件事做成一条可复用、可审计、可回归的工程流水线。

如果你经历过赛前通宵补 Dockerfile、线上临时修 start.sh、打包后才发现平台契约不满足，这份 README 就是为这种场景写的。你可以从本页直接完成：安装、提案确认、单题渲染、场景编排、本地回归、发布打包。

## v2.0.2 重点更新

### v1.5.0：治理基线与运行时兼容

`v1.5.0` 把工程治理从“能跑”提升到“可持续维护”：

- 建立 Python 主线治理脚本：`doc_guard.py`、`release_build.py`、`generate_sbom.py`、`sync.py`、`publish_guard.py`。
- 引入运行时档位：`runtime_profiles.yaml`，并在 `derive_config.py` 输出 runtime 候选与证据。
- 固化平台硬约束与文档一致性，减少“口头约定”和实现偏差。

### v2.0.0：能力面扩展到 profile/defense + BaseUnit + Scenario

`v2.0.0` 是真正的能力跃迁版本：

- 配置模型升级为 `challenge.profile + challenge.defense` 主口径，保留 `challenge.rdg` 兼容输入。
- 平台硬契约升级为每次都交付 `Dockerfile + start.sh + changeflag.sh`。
- 新增 `stack=secops`、`stack=baseunit`，支持安全运维题与服务基座最小单元。
- 新增 `render_component.py`、`render_scenario.py`、`validate_scenario.py`。
- 落地 AWDP 固定补丁契约：`patch/src/ + patch/patch.sh + patch_bundle.tar.gz`。

### v2.0.1：收口补丁与可重复构建

`v2.0.1` 重点处理“最后一公里”的稳定性：

- 补齐 `scenario-vulhub-like-basic`，给出 Vulhub-like 迁移示例。
- 修复 `stacks.yaml` 重复定义风险，`load_stack_defs` 对重复 id 直接报错。
- AWDP 补丁包改为确定性打包，避免回归后出现无意义二进制漂移。

### v2.0.2：中文默认 + 文档全量增强

`v2.0.2` 不改运行时行为，专注文档交付体验：

- `README.md` 改为中文默认完整手册。
- 英文、日文 README 升级为完整等价内容，不再是短入口。
- 增加 AI 编程工具实战章节（Codex、Cursor、Trae、Claude Code、Copilot Chat、Aider）。
- 增加逐模式构建手册（Jeopardy / RDG / AWD / AWDP / SecOps / BaseUnit / Vulhub-like）。
- 增加文件级目录索引、FAQ、排障与发布验收清单。
- 删除“参考资料”章节，改为仓库内文档与命令直达。

## 核心能力矩阵

| 能力 | 入口脚本 | 作用 | 产出 |
|---|---|---|---|
| 自动提案 | `src/CloverSec-CTF-Build-Dockerizer/scripts/derive_config.py` | 推断栈/端口/启动命令/runtime/profile 信号 | `config_proposal` |
| 提案解析 | `src/CloverSec-CTF-Build-Dockerizer/scripts/parse_config_block.py` | 把 `CONFIG PROPOSAL` 转成规范 `challenge.yaml` | 标准化配置 |
| 单题渲染 | `src/CloverSec-CTF-Build-Dockerizer/scripts/render.py` | 生成平台交付物 | `Dockerfile/start.sh/changeflag.sh/(flag可选)` |
| 合规校验 | `src/CloverSec-CTF-Build-Dockerizer/scripts/validate.sh` | 平台契约与风险规则检查 | `ERROR/WARN/INFO` |
| 组件渲染 | `src/CloverSec-CTF-Build-Dockerizer/scripts/render_component.py` | 组件+版本最小单元生成 | 可直接 `docker build` 的目录 |
| 场景渲染 | `src/CloverSec-CTF-Build-Dockerizer/scripts/render_scenario.py` | 多服务本地编排渲染 | 服务目录 + `docker-compose.yml` |
| 场景校验 | `src/CloverSec-CTF-Build-Dockerizer/scripts/validate_scenario.py` | 校验 mode/profile/端口/AWDP 补丁契约 | pass/fail |
| 样例回归 | `src/CloverSec-CTF-Build-Dockerizer/scripts/validate_examples.sh` | 批量验证 examples 与 scenarios | 汇总结果 |
| 冒烟测试 | `src/CloverSec-CTF-Build-Dockerizer/scripts/smoke_test.sh` | 构建级别快速回归 | pass/fail |
| 发布打包 | `scripts/release_build.sh` / `scripts/publish_release.sh` | 生成资产并发布 tag/release | zip/sbom/deps |

## 一键安装与技能发现

先验证技能可发现，再执行安装：

```bash
npx -y skills add . --list

npx -y skills add \
  https://github.com/D1a0y1bb/CloverSec-CTF-Build-Dockerizer-skill \
  --skill cloversec-ctf-build-dockerizer \
  --agent codex -y
```

安装后，建议先用示例目录做一次完整闭环，确认本机 Docker 与脚本依赖可用。

## 快速开始

### Agent-Orchestrated 流程（推荐）

标准提示词（建议直接复制）：

```text
请使用 CloverSec-CTF-Build-Dockerizer 处理当前题目目录。
先运行自动探测并输出 CONFIG PROPOSAL（含证据），
我确认后再生成 Dockerfile/start.sh/changeflag.sh 并执行 validate。
```

快捷业务提示词（懒人版）：

```text
当前 src 是我的 CTF 题目源码，请按平台交付规范构建完整容器并完成校验。
```

### 手动命令链

```bash
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/derive_config.py --project-dir . --format json --pretty
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/render.py --config challenge.yaml --output .
bash src/CloverSec-CTF-Build-Dockerizer/scripts/validate.sh Dockerfile start.sh challenge.yaml
```

### 运行时档位选择（PHP/Node/Java）

```bash
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/render.py \
  --config challenge.yaml \
  --runtime-profile php74-apache \
  --output .
```

镜像优先级规则：`--base-image > --runtime-profile > challenge.base_image > infer/default`。

## AI 编程工具实战用法

本章不是讲概念，而是给你可直接复制的提示词与验收命令。每个工具都按同一结构：调用方式、推荐提示词、错误重试提示词、验收命令。

### Codex

调用方式：在仓库根目录对话，明确“先提案后渲染后校验后回报”。

推荐提示词模板：

```text
使用 CloverSec-CTF-Build-Dockerizer 处理当前目录。
先执行 derive_config.py 输出 CONFIG PROPOSAL（带 evidence），
等待我回复 OK 后再执行 render + validate + smoke，并给出失败项修复。
目标模式：<jeopardy|rdg|awd|awdp|secops|baseunit|scenario>。
```

错误重试提示词：

```text
不要重做全部步骤，只针对当前 ERROR 项最小修复。
修复后仅重跑必要校验，并汇报变更文件与命令结果。
```

产物验收命令：

```bash
bash scripts/doc_guard.sh
bash src/CloverSec-CTF-Build-Dockerizer/scripts/validate_examples.sh
```

### Cursor

调用方式：在聊天窗口指定“先读 challenge.yaml / scenario.yaml，再动手修改”。

推荐提示词模板：

```text
请基于当前仓库现有脚本工作流执行，不要手写替代 render.py/validate.sh。
先给 CONFIG PROPOSAL，再按 OK 门槛执行渲染与校验。
最终需要 Dockerfile/start.sh/changeflag.sh 契约通过。
```

错误重试提示词：

```text
保留已通过项，仅修复本轮失败；
不要改动无关文件；
修复后给出可直接复制的复验命令。
```

产物验收命令：

```bash
bash src/CloverSec-CTF-Build-Dockerizer/scripts/smoke_test.sh
```

### Trae

调用方式：要求 Trae 严格按“提案确认 -> 渲染 -> 校验 -> 复盘”四阶段输出。

推荐提示词模板：

```text
你是交付工程助手。
阶段1先做 derive_config 并展示证据；
阶段2等我确认后渲染；
阶段3执行 validate/smoke；
阶段4输出风险清单和发布前检查项。
```

错误重试提示词：

```text
将失败拆分为「配置错误」「模板错误」「运行错误」三类逐项处理，
每次只修一类并立即复验。
```

产物验收命令：

```bash
npx -y skills add . --list
bash scripts/release_build.sh
```

### Claude Code

调用方式：明确要求“输出变更计划 + 实施 + 命令结果摘要”。

推荐提示词模板：

```text
请在当前仓库执行 v2 交付链路：
1) derive_config -> CONFIG PROPOSAL
2) render.py / render_component.py / render_scenario.py（按模式）
3) validate.sh / validate_scenario.py / smoke_test.sh
4) 输出失败原因、修复和剩余风险
```

错误重试提示词：

```text
忽略已经通过的步骤，聚焦最后一次失败命令。
先解释根因，再给最小补丁并复验。
```

产物验收命令：

```bash
bash scripts/doc_guard.sh
bash src/CloverSec-CTF-Build-Dockerizer/scripts/validate_examples.sh
bash src/CloverSec-CTF-Build-Dockerizer/scripts/smoke_test.sh
```

### GitHub Copilot Chat

调用方式：在 VS Code 工作区中指定“禁止偏离项目脚本链路”。

推荐提示词模板：

```text
请只使用仓库已有脚本（derive_config/render/validate）完成构建，
不要凭经验重写 Dockerfile。
先输出 CONFIG PROPOSAL，我确认后再执行下一步。
```

错误重试提示词：

```text
请基于最新终端报错定位到具体文件和行，
给出补丁后只重跑受影响命令。
```

产物验收命令：

```bash
bash scripts/release_build.sh
```

### Aider

调用方式：建议先手工执行一次检测，再让 Aider 修文件并复验。

推荐提示词模板：

```text
请根据以下失败日志修复仓库，目标是通过：
- bash scripts/doc_guard.sh
- bash src/CloverSec-CTF-Build-Dockerizer/scripts/validate_examples.sh
保留现有架构，不做大规模重构。
```

错误重试提示词：

```text
当前补丁范围过大，请改为最小改动策略：
只改与失败直接相关的文件，并说明每个改动对应哪条报错。
```

产物验收命令：

```bash
git diff --stat
bash scripts/doc_guard.sh
```

## 竞赛模式构建手册

### Jeopardy（Web / Pwn / AI）

适用：常规解题模式，默认 `profile=jeopardy`。

最小流程：

```bash
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/render.py \
  --config src/CloverSec-CTF-Build-Dockerizer/examples/node-basic/challenge.yaml \
  --output /tmp/jeopardy-node

bash src/CloverSec-CTF-Build-Dockerizer/scripts/validate.sh \
  /tmp/jeopardy-node/Dockerfile \
  /tmp/jeopardy-node/start.sh \
  /tmp/jeopardy-node/challenge.yaml
```

### RDG

适用：防守运维 + check_service 计分场景，通常使用 `stack=rdg`。

最小流程：

```bash
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/render.py \
  --config src/CloverSec-CTF-Build-Dockerizer/examples/rdg-python-ssti-basic/challenge.yaml \
  --output /tmp/rdg-python

bash src/CloverSec-CTF-Build-Dockerizer/scripts/validate.sh \
  /tmp/rdg-python/Dockerfile \
  /tmp/rdg-python/start.sh \
  /tmp/rdg-python/challenge.yaml
```

### AWD

适用：攻防混合赛，通常基于现有 Web/Pwn 栈叠加 `profile=awd` 与运维入口。

关键点：本项目不新增 `stack=awd`，而是“现有 stack + `profile=awd`”。

场景流程：

```bash
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/render_scenario.py \
  --config src/CloverSec-CTF-Build-Dockerizer/examples/scenario-awd-basic/scenario.yaml \
  --output /tmp/scenario-awd

python3 src/CloverSec-CTF-Build-Dockerizer/scripts/validate_scenario.py \
  --output /tmp/scenario-awd
```

### AWDP

适用：attack + fix，选手提交补丁包而不是直接 SSH 改环境。

固定补丁契约：

- `patch/src/`
- `patch/patch.sh`
- `patch_bundle.tar.gz`

最小流程：

```bash
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/render.py \
  --config src/CloverSec-CTF-Build-Dockerizer/examples/node-awdp-basic/challenge.yaml \
  --output /tmp/awdp-node

bash src/CloverSec-CTF-Build-Dockerizer/scripts/validate.sh \
  /tmp/awdp-node/Dockerfile \
  /tmp/awdp-node/start.sh \
  /tmp/awdp-node/challenge.yaml
```

### SecOps

适用：安全运维与加固配置类题目。

关键点：`stack=secops + profile=secops` 是独立语义，不再混入 RDG。

最小流程：

```bash
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/render.py \
  --config src/CloverSec-CTF-Build-Dockerizer/examples/secops-nginx-basic/challenge.yaml \
  --output /tmp/secops-nginx

bash src/CloverSec-CTF-Build-Dockerizer/scripts/validate.sh \
  /tmp/secops-nginx/Dockerfile \
  /tmp/secops-nginx/start.sh \
  /tmp/secops-nginx/challenge.yaml
```

### BaseUnit（指定版本服务包最小单元）

适用：快速生成某组件某版本的纯服务基座镜像，避免现场手工编译踩坑。

首批组件：`mysql`、`redis`、`sshd`、`ttyd`、`apache`、`nginx`、`tomcat`、`php-fpm`、`vsftpd`、`weblogic`。

最小流程：

```bash
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/render_component.py --list

python3 src/CloverSec-CTF-Build-Dockerizer/scripts/render_component.py \
  --component redis \
  --variant 7.2-alpine \
  --profile jeopardy \
  --output /tmp/baseunit-redis

bash src/CloverSec-CTF-Build-Dockerizer/scripts/validate.sh \
  /tmp/baseunit-redis/Dockerfile \
  /tmp/baseunit-redis/start.sh \
  /tmp/baseunit-redis/challenge.yaml
```

### Vulhub-like（多服务漏洞环境迁移）

适用：把 Vulhub 风格的多服务场景迁移到“本地 compose 编排 + 平台单服务交付”。

边界：`docker-compose.yml` 仅用于本地验证，平台交付仍是每个服务独立目录。

最小流程：

```bash
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/render_scenario.py \
  --config src/CloverSec-CTF-Build-Dockerizer/examples/scenario-vulhub-like-basic/scenario.yaml \
  --output /tmp/scenario-vulhub-like

python3 src/CloverSec-CTF-Build-Dockerizer/scripts/validate_scenario.py \
  --output /tmp/scenario-vulhub-like
```

## 平台硬契约与边界

所有渲染产物必须满足：

- 存在 `Dockerfile`。
- 存在可执行 `start.sh`。
- 存在可执行 `changeflag.sh`。
- 容器内存在 `/bin/bash`。
- Dockerfile 声明 `EXPOSE`。
- `start.sh` 启动真实服务进程，禁止空转保活。

`flag` 规则：

- 默认需要交付 `flag`。
- 显式 `include_flag_artifact=false` 时，只能放行 `flag` 缺失，不能放行 `changeflag.sh` 缺失。

Scenario 边界：

- 允许输出 `docker-compose.yml` 做本地编排。
- 平台最终交付仍是单服务目录（`Dockerfile + start.sh + changeflag.sh`）。

## Workflow 截图（从提示词到发布）

Prompt 触发：

![workflow-01](docs/assets/readme/workflow-01-quick-prompt.png)

提案确认：

![workflow-02](docs/assets/readme/workflow-02-prebuild-decision.png)

错误闭环：

![workflow-03](docs/assets/readme/workflow-03-error-closure.png)

自动产物：

![workflow-04](docs/assets/readme/workflow-04-auto-build.png)

自动校验：

![workflow-05](docs/assets/readme/workflow-05-auto-validation.png)

硬约束检查：

![workflow-06](docs/assets/readme/workflow-06-hard-check.png)

交付清单：

![workflow-07](docs/assets/readme/workflow-07-delivery-checklist.png)

## Build_test 真实样例

`Build_test/` 用来存放真实题目样例，方便你做“可重复构建 + 可重复校验”。

| 样例目录 | 栈 | 端口 | 启动命令 | 主要文件 |
|---|---|---:|---|---|
| `Build_test/CTF-NodeJs RCE-Test1` | node | 3000 | `node app.js` | `challenge.yaml` `Dockerfile` `start.sh` `app.js` |
| `Build_test/CTF-Python沙箱逃逸-Test2` | python | 5000 | `python app.py` | `challenge.yaml` `Dockerfile` `start.sh` `Build_test/CTF-Python沙箱逃逸-Test2/src/app.py` |

复验命令：

```bash
cd "Build_test/CTF-NodeJs RCE-Test1"
npm ci
bash ../../src/CloverSec-CTF-Build-Dockerizer/scripts/validate.sh Dockerfile start.sh challenge.yaml

cd "../CTF-Python沙箱逃逸-Test2"
bash ../../src/CloverSec-CTF-Build-Dockerizer/scripts/validate.sh Dockerfile start.sh challenge.yaml
```

## 文件级目录索引

### 根目录（发布与入口）

| 文件/目录 | 作用 |
|---|---|
| `README.md` | 中文默认完整手册（主入口） |
| `README.en.md` | 英文完整手册 |
| `README.ja.md` | 日文完整手册 |
| `README.zh-CN.md` | 中文兼容入口（历史链接跳转） |
| `VERSION` | 当前发布版本号 |
| `CHANGELOG.md` | 版本变更历史 |
| `LICENSE` | 开源许可证 |
| `Build_test/` | 真实题目构建回归样例 |
| `dist/` | `release_build` 生成的发布资产 |

### `scripts/`（仓库级治理与发布）

| 文件 | 作用 |
|---|---|
| `scripts/doc_guard.py` | 文档一致性门禁主实现 |
| `scripts/doc_guard.sh` | 文档门禁 Shell 入口 |
| `scripts/release_build.py` | release 打包主实现 |
| `scripts/release_build.sh` | release 打包入口 |
| `scripts/publish_guard.py` | 发布前版本/白名单守卫 |
| `scripts/publish_release.sh` | commit + push + tag + release 编排 |
| `scripts/generate_sbom.py` | SBOM 生成主实现 |
| `scripts/generate_sbom.sh` | SBOM 入口 |
| `scripts/sync.py` | 私有仓到发布仓同步逻辑 |
| `scripts/sync.sh` | 同步入口 |

### `src/CloverSec-CTF-Build-Dockerizer/data`（规则与配置数据）

| 文件 | 作用 |
|---|---|
| `schema.md` | `challenge.yaml` 输入契约 |
| `scenario_schema.md` | `scenario.yaml` 输入契约 |
| `stacks.yaml` | 栈默认值与模板映射 |
| `profiles.yaml` | profile 默认行为定义 |
| `components.yaml` | BaseUnit 组件与版本变体 |
| `runtime_profiles.yaml` | 运行时档位定义（php/node/java） |
| `patterns.yaml` | 自动探测规则 |
| `validate_rules.yaml` | `validate.sh` 规则配置 |
| `validate_scenario_rules.yaml` | scenario 校验规则配置 |
| `base_image_allowlist.yaml` | 基础镜像白名单 |
| `README.md` | data 目录说明 |

### `src/CloverSec-CTF-Build-Dockerizer/scripts`（渲染/校验核心脚本）

| 文件 | 作用 |
|---|---|
| `derive_config.py` | 自动推断 challenge 配置 |
| `parse_config_block.py` | 解析 CONFIG PROPOSAL |
| `render.py` | 单题渲染入口 |
| `render_component.py` | BaseUnit 组件渲染入口 |
| `render_scenario.py` | 场景编排渲染入口 |
| `validate.sh` | 单题契约校验入口 |
| `validate_scenario.py` | 场景契约校验入口 |
| `validate_examples.sh` | examples 批量回归 |
| `smoke_test.sh` | 冒烟测试 |
| `validate_context.py` | challenge 上下文解析辅助 |
| `autofix.py` | 常见问题自动修复辅助 |
| `detect_stack.py` | 栈识别辅助 |
| `utils.py` | 公共工具函数 |
| `cleanup_test_containers.sh` | 测试容器清理 |
| `test_runtime_profiles.sh` | runtime profiles 回归 |
| `README.md` | scripts 目录说明 |

### `src/CloverSec-CTF-Build-Dockerizer/templates`（模板库）

| 路径 | 作用 |
|---|---|
| `templates/node|php|python|java|tomcat|lamp|pwn|ai/` | Jeopardy 栈模板 |
| `templates/rdg/` | RDG 专用模板 |
| `templates/secops/` | SecOps 专用模板 |
| `templates/baseunit/` | BaseUnit 通用模板 |
| `templates/snippets/` | defense/check/changeflag 等片段 |
| `templates/README.md` | 模板目录说明 |

### `src/CloverSec-CTF-Build-Dockerizer/examples`（示例与回归输入）

| 路径 | 作用 |
|---|---|
| `examples/*-basic` | 单题最小示例（node/php/python/...） |
| `examples/node-awdp-basic` | AWDP 单题补丁契约示例 |
| `examples/secops-*-basic` | SecOps 示例 |
| `examples/baseunit-*` | BaseUnit 示例 |
| `examples/scenario-awd-basic` | AWD 场景示例 |
| `examples/scenario-awdp-basic` | AWDP 场景示例 |
| `examples/scenario-vulhub-like-basic` | Vulhub-like 迁移示例 |
| `examples/README.md` | 示例目录说明 |

### `src/CloverSec-CTF-Build-Dockerizer/docs`（设计文档）

| 文件 | 作用 |
|---|---|
| `architecture_overview.md` | 架构总览 |
| `platform_contract.md` | 平台硬契约说明 |
| `stack_cookbook.md` | 各栈构建建议 |
| `directory_guide.md` | 目录设计说明 |
| `troubleshooting.md` | 常见故障排查 |
| `beginner_guide.md` | 新手入门流程 |

## FAQ 与常见排障

### Q1：为什么必须有 `/start.sh`、`/changeflag.sh`、`/bin/bash`？

这是平台运行契约。缺任一项都可能导致题目无法被平台正常启动或重置。

### Q2：为什么我设置了 `include_flag_artifact=false` 还报错？

这个开关只允许 `flag` 缺失，不允许 `changeflag.sh` 缺失。请检查渲染目录里 `changeflag.sh` 是否存在且可执行。

### Q3：AWD 和 SecOps 看起来很像，怎么选？

- 你要做攻防对抗，选“现有栈 + `profile=awd`”。
- 你要做加固运维，选 `stack=secops + profile=secops`。

### Q4：AWDP 为什么不是直接 SSH 修题？

AWDP 的关键是“补丁提交与审计”，不是现场运维。选手通过 `patch/src + patch.sh + tar.gz` 提交修复，平台再自动应用。

### Q5：Vulhub-like 场景为什么不能直接拿 compose 当最终交付？

因为目标平台要求单服务交付目录。`scenario` 的 compose 只用于你本地联调与验证拓扑。

### Q6：`npx -y skills add . --list` 和 Release 资产有关系吗？

没有直接依赖。前者验证技能可发现，后者是版本归档分发。

## 维护、贡献与发布

发布前最小检查清单：

```bash
bash scripts/doc_guard.sh
bash src/CloverSec-CTF-Build-Dockerizer/scripts/validate_examples.sh
bash src/CloverSec-CTF-Build-Dockerizer/scripts/smoke_test.sh
npx -y skills add . --list
bash scripts/release_build.sh
```

正式发布：

```bash
bash scripts/publish_release.sh --version v2.0.2
```

如果遇到远端 tag/release 冲突或认证失败，应该停止发布流程并先处理阻塞，不要临时修改版本号绕过。

## License

本项目使用 [MIT License](LICENSE)。
