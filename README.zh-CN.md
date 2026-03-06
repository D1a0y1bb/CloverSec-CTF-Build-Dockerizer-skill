# CloverSec-CTF-Build-Dockerizer

<p align="center">
  <a href="README.md"><strong>English</strong></a>
  <span> · </span>
  <a href="README.ja.md"><strong>日本語</strong></a>
  <span> · </span>
  <a href="README.en.md"><strong>Legacy English Entry</strong></a>
</p>

<p align="center">
  <a href="https://github.com/D1a0y1bb/CloverSec-CTF-Build-Dockerizer-skill/releases"><img src="https://img.shields.io/badge/version-v2.0.0-2563eb?style=for-the-badge" alt="Version" /></a>
  <a href="https://github.com/D1a0y1bb/CloverSec-CTF-Build-Dockerizer-skill"><img src="https://img.shields.io/badge/stacks-11-f59e0b?style=for-the-badge" alt="Stacks" /></a>
  <a href="https://github.com/D1a0y1bb/CloverSec-CTF-Build-Dockerizer-skill"><img src="https://img.shields.io/badge/profiles-jeopardy%2Frdg%2Fawd%2Fawdp%2Fsecops-16a34a?style=for-the-badge" alt="Profiles" /></a>
  <a href="https://github.com/D1a0y1bb/CloverSec-CTF-Build-Dockerizer-skill/releases/tag/v2.0.0"><img src="https://img.shields.io/badge/release-zip%2Bsbom-10b981?style=for-the-badge" alt="Release Asset" /></a>
</p>

<p align="center"><code><strong>VERSION</strong>: v2.0.0</code></p>

四叶草安全题目容器交付引擎 `v2.0.0`，用于 Jeopardy / RDG / AWD / AWDP / SecOps / BaseUnit / Scenario 本地编排的统一构建与校验。

## v2.0.0 重点更新

- 平台交付硬契约升级：每次渲染默认产出 `Dockerfile + start.sh + changeflag.sh`。
- 配置模型升级：`challenge.profile` + `challenge.defense` 成为主口径，`challenge.rdg` 保留兼容输入。
- 新增独立栈：`stack=secops`、`stack=baseunit`。
- 新增组件最小单元渲染：
  - `data/components.yaml`
  - `scripts/render_component.py`
- 新增场景编排链路：
  - `scripts/render_scenario.py`
  - `scripts/validate_scenario.py`
  - `data/scenario_schema.md`
- 新增 AWDP 固定补丁契约：
  - `patch/src/`
  - `patch/patch.sh`
  - `patch_bundle.tar.gz`
- 完整多语言文档：英文 / 中文 / 日文。

## 核心能力矩阵

| 能力 | 入口脚本 | 作用 | 输出 |
|---|---|---|---|
| 自动提案 | `src/CloverSec-CTF-Build-Dockerizer/scripts/derive_config.py` | 推断栈/端口/启动命令/profile | `config_proposal` |
| 提案解析 | `src/CloverSec-CTF-Build-Dockerizer/scripts/parse_config_block.py` | 解析 `CONFIG PROPOSAL` 到 `challenge.yaml` | 标准化配置 |
| 单题渲染 | `src/CloverSec-CTF-Build-Dockerizer/scripts/render.py` | 生成平台交付件 | `Dockerfile/start.sh/changeflag.sh/(flag可选)` |
| 组件渲染 | `src/CloverSec-CTF-Build-Dockerizer/scripts/render_component.py` | 组件+版本最小单元构建 | 可直接构建目录 |
| 场景渲染 | `src/CloverSec-CTF-Build-Dockerizer/scripts/render_scenario.py` | 多服务本地场景编排 | 服务目录 + `docker-compose.yml` |
| 场景校验 | `src/CloverSec-CTF-Build-Dockerizer/scripts/validate_scenario.py` | 校验 profile/端口/AWDP 契约 | pass/fail |
| 契约校验 | `src/CloverSec-CTF-Build-Dockerizer/scripts/validate.sh` | 平台硬规则 + 风险检查 | ERROR/WARN/INFO |
| 样例回归 | `src/CloverSec-CTF-Build-Dockerizer/scripts/validate_examples.sh` | 全量样例回归 | 汇总结果 |

## 快速开始

### 1）渲染单题目录

```bash
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/render.py --config challenge.yaml --output .
bash src/CloverSec-CTF-Build-Dockerizer/scripts/validate.sh Dockerfile start.sh challenge.yaml
```

### 2）渲染 BaseUnit 组件

```bash
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/render_component.py \
  --component redis \
  --variant 7.2-alpine \
  --output /tmp/baseunit-redis
```

### 3）渲染 AWD/AWDP 本地场景

```bash
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/render_scenario.py \
  --config src/CloverSec-CTF-Build-Dockerizer/examples/scenario-awd-basic/scenario.yaml \
  --output /tmp/scenario-awd

python3 src/CloverSec-CTF-Build-Dockerizer/scripts/validate_scenario.py \
  --output /tmp/scenario-awd
```

## 平台交付契约（V2）

每次渲染都必须满足：

- 镜像中存在且可执行 `/start.sh`
- 镜像中存在且可执行 `/changeflag.sh`
- 镜像中存在 `/bin/bash`
- Dockerfile 存在 `EXPOSE`
- `start.sh` 必须启动真实服务，禁止空转保活

`/flag` 规则：

- 默认必须交付
- 仅当防御 profile 场景显式设置 `include_flag_artifact=false` 时可放行（常见于 RDG/AWDP/SecOps 的 check-service 题型）

## V2 profile/defense 口径

支持 profile：

- `jeopardy`
- `rdg`
- `awd`
- `awdp`
- `secops`

优先级：

- 主输入：`challenge.defense`
- 兼容输入：`challenge.rdg`
- 引擎内部归一化后统一渲染行为

## BaseUnit 首批组件（10类）

- `mysql`
- `redis`
- `sshd`
- `ttyd`
- `apache`
- `nginx`
- `tomcat`
- `php-fpm`
- `vsftpd`
- `weblogic`

可用 `render_component.py --list` 查看所有变体。

## AWD/AWDP/Vulhub-like 边界

Scenario 生成的 `docker-compose.yml` 仅用于本地编排验证，不作为平台最终交付物。

平台最终交付仍是单服务目录中的：

- `Dockerfile`
- `start.sh`
- `changeflag.sh`

### Vulhub-like 迁移路径

从 Vulhub 这类多服务编排迁移时，建议按下面做：

1. 先把每个服务拆成“单题目录”或 `baseunit` 组件变体
2. 再用 `scenario.yaml` 描述服务关系与端口映射
3. 用 `render_scenario.py` + `validate_scenario.py` 做本地回归
4. 最后把每个服务目录按单容器交付到平台

可直接运行的 Vulhub-like 迁移示例：

```bash
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/render_scenario.py \
  --config src/CloverSec-CTF-Build-Dockerizer/examples/scenario-vulhub-like-basic/scenario.yaml \
  --output /tmp/scenario-vulhub-like

python3 src/CloverSec-CTF-Build-Dockerizer/scripts/validate_scenario.py \
  --output /tmp/scenario-vulhub-like
```

## AWDP 补丁流程

当服务渲染为 `profile=awdp` 时，必须存在：

- `patch/src/`
- 可执行 `patch/patch.sh`
- 包含上述内容的 `patch_bundle.tar.gz`

## SecOps 与 AWD 差异

| 维度 | AWD | SecOps |
|---|---|---|
| 核心目标 | 攻防对抗 + 可用性维护 | 安全加固与配置治理 |
| 常见实现 | web/pwn 栈 + `profile=awd` | `stack=secops` + `profile=secops` |
| 登录运维 | 通常开启 | 按安全策略可开关 |
| 评分模式 | 攻防平台逻辑或服务检查 | 服务检查 + 加固检查 |

## 验收与发布

```bash
bash scripts/doc_guard.sh
bash src/CloverSec-CTF-Build-Dockerizer/scripts/validate_examples.sh
bash src/CloverSec-CTF-Build-Dockerizer/scripts/smoke_test.sh
npx -y skills add . --list
bash scripts/release_build.sh
bash scripts/publish_release.sh --version v2.0.0
```

## 文档索引

- 技能协议：`src/CloverSec-CTF-Build-Dockerizer/SKILL.md`
- 输入 Schema：`src/CloverSec-CTF-Build-Dockerizer/data/schema.md`
- 平台契约：`src/CloverSec-CTF-Build-Dockerizer/docs/platform_contract.md`
- 架构总览：`src/CloverSec-CTF-Build-Dockerizer/docs/architecture_overview.md`
- 栈手册：`src/CloverSec-CTF-Build-Dockerizer/docs/stack_cookbook.md`
- 场景 Schema：`src/CloverSec-CTF-Build-Dockerizer/data/scenario_schema.md`

## 参考资料

- [Vulhub](https://github.com/vulhub/vulhub)
- [Quick Start CTF mode docs](https://quickstart-ctf.github.io/quickstart/mode.html)
- [AWDP patch workflow reference (CN)](https://www.cn-sec.com/archives/1948396.html)
