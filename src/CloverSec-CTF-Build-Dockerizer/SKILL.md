---
name: cloversec-ctf-build-dockerizer
description: 四叶草安全-创研中心竞赛专用题目容器构建 Skills，面向 Jeopardy/RDG/AWD/AWDP/SecOps/BaseUnit/Bundle/Linux-QEMU/Scenario 本地编排：自动探测、渲染 Dockerfile/start.sh/changeflag.sh/flag/check，并执行契约校验。用于把题目源码、历史 Dockerfile、compose/Vulhub-like 环境、Linux kernel QEMU 题目或 Bundle 老环境整理为可验证的容器交付件。
metadata:
  short-description: 四叶草安全题目容器交付、BaseUnit/Bundle/Linux-QEMU 构建与 Scenario 编排
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

本 Skill 不替代题目业务设计、漏洞修复或 PoC 编写，也不把原始 `docker-compose.yml` 直接声明为平台最终交付物。

## 首选入口

本文中的 `scripts/`、`docs/`、`data/`、`templates/`、`examples/` 均相对于本 `SKILL.md` 所在目录。使用已安装 Skill 时，不要给这些路径加源码仓库前缀；先解析 Skill 根目录真实位置，再读取或执行对应文件。

输入提示：可直接给 `<path/to/challenge.yaml>`，也可用 `--project-dir <path/to/challenge>` 指向题目目录。

优先使用 `workflow.py auto-render`。它会审计输入、必要时推导 `challenge.yaml`、生成平台交付文件，并执行静态契约校验：

```bash
python3 scripts/workflow.py auto-render --project-dir <题目目录>
```

需要先看输入审计或状态时使用：

```bash
python3 scripts/workflow.py intake --project-dir <题目目录>
python3 scripts/workflow.py status --project-dir <题目目录>
```

`auto-render` 只代表平台文件生成和静态契约检查通过，不代表题目已经可解，也不代表 Docker build/run/export 已执行。真实 Docker 操作仍需要用户授权。

熟练用户已经确认 `challenge.yaml` 时，可以直接调用底层脚本：

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
- Bundle 支持固定 Recipe 和显式 custom 组合；custom 组合必须由用户给出安装命令、启动命令、端口和服务清单，不做自动版本求解。
- 历史题复刻必须确认原始运行时版本、镜像架构和题目业务 flag 路径；`validate.sh` 通过只代表平台交付契约成立，不代表题目已经可解。
- 如果题目程序不读取 `/flag`，在 `challenge.flag.sync_paths` 配置业务路径；同步发生在平台调用 `/changeflag.sh` 时，启动脚本只保证 `/flag` 和模板内显式兼容的常见路径。只有用户明确说明平台不会调用 `/changeflag.sh` 时，才把启动时同步写成题目特定兼容逻辑。需要证明题目入口可用时，在 `challenge.verification.solve_probe` 或 `smoke_assert.yaml` 写断言，并执行 `bash scripts/smoke_test.sh --case <example-name>`；内置示例用 `python-flask-basic`。

平台契约细节读取 `docs/platform_contract.md`。

## 输入路由

| 输入状态 | 推荐路径 | 读取资料 |
|---|---|---|
| 明确 `challenge.yaml`，低风险 | `workflow.py auto-render --project-dir <题目目录>` | `data/schema.md`、`docs/stack_cookbook.md` |
| 目录里有旧 Dockerfile、零散脚本、多栈线索或默认启动命令不可信 | 先执行 `workflow.py intake` 看风险；未触发阻塞时执行 `workflow.py auto-render` | `scripts/README.md`、`docs/troubleshooting.md` |
| compose/Vulhub-like 输入 | `import_compose.py` -> 审查 `scenario.draft.yaml` -> 渲染 `scenario.renderable.yaml` | `data/scenario_schema.md` |
| Scenario 正向编排 | 输出服务清单和端口摘要，低风险场景继续执行 `render_scenario.py` -> `validate_scenario.py --validate-rendered` | `data/scenario_schema.md` |
| Bundle 老环境组合 | 输出 Recipe/custom 摘要，低风险组合继续执行 `render_bundle.py` -> `validate_bundle.py` -> `validate.sh` | `docs/bundle_design.md`、`data/bundle_recipes.yaml` |
| Linux kernel CVE/LPE | `stack=linux-qemu`，需要启动 guest、写入 guest flag 或复现 PoC 时再跑 `linux_qemu_manual_check.sh` | `docs/linux_qemu_manual_validation.md` |
| RDG/SecOps 需要 check 脚本 | `generate_check_stub.py` 生成骨架，人工确认后移除 `CHECK_REVIEW_REQUIRED` | `docs/validation_guide.md` |

## 自动生成门

普通源码题、已有 Dockerfile、单服务 Web/Pwn 服务题默认允许 `auto-render`。缺少端口、Flag 路径这类信息时，脚本会写入 `unconfirmed` 和校验摘要，不把它当成题目已通过。

以下情况不能自动生成，需要把问题列给用户判断：

- high_risk 输入
- unsupported 输入
- compose/Vulhub-like 结构
- Scenario、本地多服务编排或 Bundle 老环境组合
- Linux-QEMU VM 资产缺失或疑似占位
- cPanel/WHM 控制面板类输入
- 完全没有启动方式证据

保留手动模式：

```bash
python3 scripts/render.py \
  --config challenge.yaml \
  --output . \
  --manual \
  --reason "trusted migration from reviewed delivery"
```

使用 `--manual` 时必须写明原因，并在结果中保留 manual override 记录。

如果人工修改了 `challenge.yaml`，可以重新执行 `workflow.py auto-render --project-dir <题目目录>`，让静态校验重新生成摘要。

## 人工判断边界

本 Skill 会主动生成平台交付文件，但不会替用户判断题目业务质量。以下内容要在输出里写清楚：

- 端口和启动命令来自哪里
- 上游 Dockerfile/compose 只作为迁移输入
- `validate.sh` 通过只代表平台文件契约通过
- 真实 Docker build/run/export 未执行时必须明说
- 题目是否可解、动态 Flag 是否真的进入业务逻辑，需要后续验证

Scenario、Bundle、Linux-QEMU、高风险依赖、多服务拆分、需要 privileged/eBPF/tc/KVM/jail 的题目，要先把问题列给用户，不自动执行高风险运行。普通源码题、已有 Dockerfile/compose 题默认直接生成平台交付件并做静态校验。

1. 技术栈 + profile / runtime profile
2. 容器端口
3. WORKDIR
4. 启动命令
5. `app_src` -> `app_dst`

详细提案格式读取 `docs/orchestrated_workflow.md`，新手说明读取 `docs/beginner_guide.md`，解析使用 `parse_config_block.py`。

## 默认运行顺序

本节命令用于普通容器题的自动处理。只有真实启动未知容器、高权限运行、外部网络访问或题目取舍无法判断时，才停下让用户决定。

常规题目：

```bash
python3 scripts/derive_config.py --project-dir <题目目录> --format json --pretty
```

```bash
python3 scripts/render.py --config <题目目录>/challenge.yaml --output <题目目录>
bash scripts/validate.sh <题目目录>/Dockerfile <题目目录>/start.sh <题目目录>/challenge.yaml
```

Scenario：

先输出服务清单、端口和交付目录摘要；低风险场景可继续生成，涉及高风险运行时再停下：

```bash
python3 scripts/render_scenario.py --config scenario.yaml --output /tmp/scenario --accepted --reason "low-risk scenario render"
python3 scripts/validate_scenario.py --output /tmp/scenario --validate-rendered
```

Bundle：

先输出 recipe/custom、端口、服务列表和支持等级；低风险组合可继续生成，涉及高风险运行时再停下：

```bash
python3 scripts/render_bundle.py --recipe legacy-centos7-python39-mysql57-redis5 --output /tmp/bundle
python3 scripts/validate_bundle.py --bundle-dir /tmp/bundle
bash scripts/validate.sh /tmp/bundle/Dockerfile /tmp/bundle/start.sh /tmp/bundle/challenge.yaml
```

Check-service 骨架：

```bash
python3 scripts/generate_check_stub.py --type http --output check/check.sh --target-port 80 --path /
```

生成脚本默认带 `CHECK_REVIEW_REQUIRED`，健康检查和业务断言审查后才能移除。

## 按需读取索引

| 需要的信息 | 文件 |
|---|---|
| 输入字段、`challenge.yaml` 结构 | `data/schema.md` |
| 栈选择、运行时档位、Linux-QEMU 配置示例 | `docs/stack_cookbook.md` |
| 平台 `/start.sh`、`/flag`、`/changeflag.sh` 契约 | `docs/platform_contract.md` |
| 校验项、错误码、check-service 门禁 | `docs/validation_guide.md` |
| 题目入口业务断言、动态 flag 路径和 smoke probe 示例 | `docs/solve_probe_recipes.md` |
| 自动推导、方案摘要和高风险确认边界 | `docs/orchestrated_workflow.md` |
| 脚本入口和常用命令 | `scripts/README.md` |
| Scenario schema 和 compose import 边界 | `data/scenario_schema.md` |
| Bundle/Recipe 边界 | `docs/bundle_design.md` |
| Linux-QEMU guest 启动、guest flag 与 PoC 验证 | `docs/linux_qemu_manual_validation.md` |
| 常见 render/validate/build/run 问题 | `docs/troubleshooting.md` |
| 目录职责 | `docs/directory_guide.md` |

读取原则：只读当前任务需要的文件，避免把 schema、栈手册和排障手册一次性全部读入上下文。

## Docker Artifact 输出

完成 `render.py` 和 `validate.sh` 后，需要为归档流程生成 Docker artifact 计划时，使用：

```bash
python3 scripts/docker_artifacts.py plan \
  --project-dir <题目目录> \
  --image-name cloversec/example:latest \
  --tar-path archive/example.tar \
  --port 18080:80 \
  --output docker_artifacts.json
```

该脚本默认使用 `linux/amd64`，并输出：

- `environment`
- `docker_artifacts`
- `xlsx_fields`

需要真实执行 Docker 时，只在用户确认后运行：

```bash
python3 scripts/docker_artifacts.py execute --plan docker_artifacts.json --steps build,run,save_image_tar,inspect_image --output docker_artifacts.executed.json
```

需要检查镜像架构时，先导出 inspect JSON，再校验：

```bash
docker image inspect cloversec/example:latest > image.inspect.json
python3 scripts/docker_artifacts.py validate-artifacts --plan docker_artifacts.executed.json --inspect-json image.inspect.json --output docker_artifacts.validated.json
```

不要把未执行的 Docker build/run/save/load 说成已验证。

## 输出汇报要求

完成任务时必须说明：

- 修改了哪些功能层面的行为或文档入口。
- 执行了哪些验证命令。
- 哪些检查没执行，以及原因。

不要把 WARN 当成 ERROR，也不要把未执行的 Docker build/QEMU boot 说成已经验证。
