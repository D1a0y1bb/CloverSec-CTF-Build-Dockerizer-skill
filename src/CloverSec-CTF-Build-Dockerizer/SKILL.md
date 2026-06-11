---
name: cloversec-ctf-build-dockerizer
description: 四叶草安全-创研中心竞赛专用题目容器构建 Skills，面向 Jeopardy/RDG/AWD/AWDP/SecOps/BaseUnit/Bundle/Linux-QEMU/Scenario 本地编排：自动探测、渲染 Dockerfile/start.sh/changeflag.sh/flag/check，并执行契约校验。用于把题目源码、历史 Dockerfile、compose/Vulhub-like 环境、Linux kernel QEMU 题目或固定 Recipe 老环境整理为可验证的容器交付件。
metadata:
  short-description: 四叶草安全题目容器交付、BaseUnit/Bundle/Linux-QEMU 构建与 Scenario 编排
argument-hint: "[path/to/challenge.yaml] 或 --project-dir path/to/challenge"
disable-model-invocation: true
allowed-tools:
  - Bash
  - Read
  - Write
  - Glob
  - Grep
---

# CloverSec-CTF-Build-Dockerizer

## 任务定位

把 CTF 题目源码、历史交付件、固定服务基座、Bundle 老环境、Linux-QEMU 内核题和 Scenario 本地编排转换为符合四叶草安全-创研中心平台契约的 Docker 交付目录。

默认交付件：

- `Dockerfile`
- `start.sh`
- `changeflag.sh`
- `flag`，可按受支持 defense profile 的 `include_flag_artifact=false` 放行
- `check/check.sh`，仅在 RDG/SecOps/check-service 场景生成

本 Skill 不替代题目业务设计、漏洞修复、PoC 编写、外部平台发布，也不把原始 `docker-compose.yml` 直接声明为平台最终交付物。

## 首选入口

本文中的 `scripts/`、`docs/`、`data/`、`templates/`、`examples/` 均相对于本 `SKILL.md` 所在目录。使用已安装 Skill 时，不要给这些路径加源码仓库前缀；先解析 Skill 根目录真实位置，再读取或执行对应文件。

优先使用 `workflow.py`，让输入审计、Proposal Gate、渲染和校验有状态记录：

```bash
python3 scripts/workflow.py intake --project-dir <题目目录>
python3 scripts/workflow.py propose --project-dir <题目目录>
python3 scripts/workflow.py accept --project-dir <题目目录>
python3 scripts/workflow.py render --project-dir <题目目录>
python3 scripts/workflow.py validate --project-dir <题目目录>
```

低风险且字段明确的 `challenge.yaml` 可直接调用 `render.py`：

```bash
python3 scripts/render.py --config challenge.yaml --output .
bash scripts/validate.sh Dockerfile start.sh challenge.yaml
```

## 必须遵守

- 平台启动入口固定为 `/start.sh`；`start.sh` 必须可执行并启动真实服务。
- 镜像内必须存在 `/bin/bash`，因为平台动态 flag 调用依赖 Bash。
- 默认必须提供 `/flag` 且可读；只有受支持 defense profile 显式设置 `include_flag_artifact=false` 时才放行。
- 单服务必须使用 `exec` 作为主进程；多服务必须有真实前台主进程，不能用空转命令保活。
- `Dockerfile EXPOSE`、`challenge.expose_ports` 和运行端口必须一致。
- RDG/SecOps 的 `check/check.sh` 必须是真实检查脚本；`CHECK_IMPLEMENT_ME`、`CHECK_REVIEW_REQUIRED`、短脚本直接 `exit 0` 都会被 `validate.sh` 阻断。
- Linux-QEMU 的漏洞内核运行在 QEMU guest 内，外层 Docker 仍按 `/start.sh` 启动；默认使用 TCG，不默认要求 `/dev/kvm`、`--privileged` 或开放 QEMU monitor。
- Scenario 只用于本地多服务编排和逐服务验证，平台最终交付仍以单服务目录为准。
- Bundle 只支持固定 Recipe 组合；不支持的组合必须返回 `BUNDLE_UNSUPPORTED_COMBINATION`，不能自动改成别的栈。

平台契约细节读取 `docs/platform_contract.md`。

## 输入路由

| 输入状态 | 推荐路径 | 读取资料 |
|---|---|---|
| 明确 `challenge.yaml`，低风险 | 输出方案摘要，用户 `OK` 后执行 `render.py` -> `validate.sh` | `data/schema.md`、`docs/stack_cookbook.md` |
| 目录里有旧 Dockerfile、零散脚本、多栈线索或默认启动命令不可信 | `workflow.py intake/propose/accept/render/validate` | `scripts/README.md`、`docs/troubleshooting.md` |
| compose/Vulhub-like 输入 | `import_compose.py` -> 审查 `scenario.draft.yaml` -> 渲染 `scenario.renderable.yaml` | `data/scenario_schema.md` |
| Scenario 正向编排 | 输出服务清单和端口摘要，用户 `OK` 后执行 `render_scenario.py` -> `validate_scenario.py --validate-rendered` | `data/scenario_schema.md` |
| 固定老环境组合 | 输出 Recipe 摘要，用户 `OK` 后执行 `render_bundle.py` -> `validate_bundle.py` -> `validate.sh` | `docs/bundle_design.md`、`data/bundle_recipes.yaml` |
| Linux kernel CVE/LPE | `stack=linux-qemu`，release/manual 再跑 `linux_qemu_manual_check.sh` | `docs/linux_qemu_manual_validation.md` |
| RDG/SecOps 需要 check 脚本 | `generate_check_stub.py` 生成骨架，人工确认后移除 `CHECK_REVIEW_REQUIRED` | `docs/validation_guide.md` |
| 维护本 Skill 源码仓库 | 在源码仓库根目录执行发布治理脚本 | `README.md`、`CHANGELOG.md`、源码仓库 `scripts/` |

## Proposal Gate

以下情况不能直接渲染，必须先生成 proposal 并接受：

- mixed/dirty/high_risk 输入
- `audit_input.py` 或 `derive_config.py` 输出 `gates=true`
- compose/Vulhub-like 结构
- Linux-QEMU VM 资产缺失或疑似占位
- cPanel/WHM 控制面板类输入
- 启动命令、端口、WORKDIR 缺少可靠证据

保留手动模式：

```bash
python3 scripts/render.py \
  --config challenge.yaml \
  --output . \
  --manual \
  --reason "trusted migration from reviewed delivery"
```

使用 `--manual` 时必须写明原因，并在结果中保留 manual override 记录。

## 交互确认规则

凡是会生成、覆盖或修改交付件的动作，都必须先给用户输出 proposal 或方案摘要，不得直接 render。明确、低风险的 `challenge.yaml` 也要先列出 stack/profile、端口、WORKDIR、启动命令和文件映射摘要，用户确认后再执行 `render.py` 或 `validate.sh`。

只读动作可以先执行，例如 `workflow.py intake`、`audit_input.py`、`derive_config.py`、读取配置和检查目录；一旦进入 `render.py`、`render_scenario.py`、`render_bundle.py`、`workflow.py render` 或会改写文件的命令，必须先取得确认。

用户确认方式只接受两种：

- 回复 `OK`
- 返回修改后的 `CONFIG PROPOSAL` YAML

用户未确认前，不得执行 `render.py`、`render_scenario.py`、`render_bundle.py` 或 `workflow.py render`。默认确认项固定为 5 个：

1. 技术栈 + profile / runtime profile
2. 容器端口
3. WORKDIR
4. 启动命令
5. `app_src` -> `app_dst`

详细提案格式读取 `docs/orchestrated_workflow.md`，新手说明读取 `docs/beginner_guide.md`，解析使用 `parse_config_block.py`。

## 运行顺序

常规题目：

```bash
python3 scripts/derive_config.py --project-dir <题目目录> --format json --pretty
python3 scripts/render.py --config <题目目录>/challenge.yaml --output <题目目录>
bash scripts/validate.sh <题目目录>/Dockerfile <题目目录>/start.sh <题目目录>/challenge.yaml
```

Scenario：

```bash
python3 scripts/render_scenario.py --config scenario.yaml --output /tmp/scenario
python3 scripts/validate_scenario.py --output /tmp/scenario --validate-rendered
```

Bundle：

```bash
python3 scripts/render_bundle.py --recipe legacy-centos7-python39-mysql57-redis5 --output /tmp/bundle
python3 scripts/validate_bundle.py --bundle-dir /tmp/bundle
bash scripts/validate.sh /tmp/bundle/Dockerfile /tmp/bundle/start.sh /tmp/bundle/challenge.yaml
```

Check-service 骨架：

```bash
python3 scripts/generate_check_stub.py --type http --output check/check.sh --target-port 80 --path /
```

生成脚本默认带 `CHECK_REVIEW_REQUIRED`，必须人工确认检查逻辑后移除。

## 按需读取索引

| 需要的信息 | 文件 |
|---|---|
| 输入字段、`challenge.yaml` 结构 | `data/schema.md` |
| 栈选择、运行时档位、Linux-QEMU 配置示例 | `docs/stack_cookbook.md` |
| 平台 `/start.sh`、`/flag`、`/changeflag.sh` 契约 | `docs/platform_contract.md` |
| 校验项、错误码、check-service 门禁 | `docs/validation_guide.md` |
| 交互确认、`CONFIG PROPOSAL` 和 `OK` 流程 | `docs/orchestrated_workflow.md` |
| 脚本入口和常用命令 | `scripts/README.md` |
| Scenario schema 和 compose import 边界 | `data/scenario_schema.md` |
| Bundle/Recipe 边界 | `docs/bundle_design.md` |
| Linux-QEMU release/manual 验证 | `docs/linux_qemu_manual_validation.md` |
| 常见 render/validate/build/run 问题 | `docs/troubleshooting.md` |
| 目录职责 | `docs/directory_guide.md` |

读取原则：只读当前任务需要的文件，避免把 schema、栈手册和排障手册一次性全部读入上下文。

## 发布前验证

使用已安装 Skill 构建题目时，在 Skill 根目录至少执行：

```bash
python3 -m py_compile scripts/*.py
find scripts -name '*.sh' -print0 | xargs -0 -n1 bash -n
bash scripts/validate_examples.sh
```

维护本 Skill 源码仓库时，源码仓库根目录另有 `doc_guard.sh`、`validate_build_test.py`、`golden_snapshot.py`、`platform_matrix.py`、`publish_guard.py`、`release_build.sh`、`publish_release.sh` 等发布治理脚本。这些脚本不属于题目目录里的交付文件，也不应被当成普通题目构建入口。

正式发布默认执行 Docker smoke，命令在源码仓库根目录运行：

```bash
bash scripts/release_build.sh --with-smoke
```

跳过 smoke 必须使用带原因的参数，例如：

```bash
python3 scripts/release_build.py --skip-smoke-with-reason "docker unavailable on this host"
```

## 输出汇报要求

完成任务时必须说明：

- 修改了哪些功能层面的行为或文档入口。
- 执行了哪些验证命令。
- 哪些检查没执行，以及原因。
- 是否改了版本、是否提交、是否推送、是否发布。

不要把 WARN 当成 ERROR，也不要把未执行的 Docker build/QEMU boot 说成已经验证。
