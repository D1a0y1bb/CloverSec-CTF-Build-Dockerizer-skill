---
name: cloversec-ctf-build-dockerizer
description: 四叶草安全-创研中心竞赛专用题目容器构建 Skills，面向 Jeopardy/RDG/AWD/AWDP/SecOps/BaseUnit/Bundle/Linux-QEMU/Scenario 本地编排：自动探测、渲染 Dockerfile/start.sh/changeflag.sh/flag/check，并执行契约校验。用于把题目源码、历史 Dockerfile、compose/Vulhub-like 环境、Linux kernel QEMU 题目或 Bundle 老环境整理为可验证的容器交付件。普通题目默认使用 direct-exec；changeflag.sh 仅用于旧 helper、Linux-QEMU 或用户明确要求。
metadata:
  short-description: 四叶草安全题目容器交付、BaseUnit/Bundle/Linux-QEMU 构建与 Scenario 编排
allowed-tools:
  - Bash
  - Read
  - Write
  - Glob
  - Grep
---

# CloverSec CTF Build Dockerizer

## 负责的结果

把题目想法、半成品源码、参考目录或历史交付件整理成一个简单、易读、可构建、可验证的 CTF 题目目录。

默认交付只保留运行需要的文件：

```text
challenge/
├── src/                 # 题目源码、静态资源或二进制
├── Dockerfile           # 镜像构建入口
├── start.sh             # 真实前台服务入口
├── challenge.yaml       # 最小平台合同
├── .dockerignore
└── flag                 # 只有启动前需要初始文件时保留
```

默认不生成 `changeflag.sh`、`FLAG_UPDATE.md`、`VERIFY.md` 或根目录机器报告。审计、构建、验证和清单写入 `.ctfbuild/`。归档文件写入交付目录之外的 `dist/`。

## 默认工作流

先读取事实，再生成目录，再做真实验证：

```text
inspect → scaffold --profile clean → build → verify → package
```

模型只使用统一入口 `scripts/ctfctl.py`：

```bash
python3 scripts/ctfctl.py inspect --project-dir <input> --format json
python3 scripts/ctfctl.py scaffold --project-dir <input> --output <output> --profile clean
python3 scripts/ctfctl.py build --project-dir <output> --image <image:tag>
python3 scripts/ctfctl.py verify --project-dir <output> --format json
python3 scripts/ctfctl.py package --project-dir <output> --output <parent>/challenge.tar.gz
```

`audit` 是 `inspect` 的兼容别名。`prepare` 是 `scaffold` 的兼容别名。普通题目不需要先读取所有历史脚本和高级资料。

## 默认规则

1. 先读取已有 `Dockerfile`、`start.sh`、`challenge.yaml`、源码入口、依赖文件和题目手册中的运行事实。
2. 保留原始输入。默认输出到独立目录。不要覆盖用户源码。
3. `clean` 只保留运行时源码和入口。它会移除缓存、附件、手册、compose 编排文件、停止脚本和明确的作者工具。
4. 已有 Dockerfile 或启动脚本时，保留运行语义。只修复明确的合同问题。
5. 没有 Dockerfile 但 `challenge.yaml` 提供 `base_image` 和 `start.cmd` 时，生成最小 Dockerfile 和 start.sh。
6. 缺少启动命令、端口、运行时或真实 Flag 路径时，不猜测业务配置。输出 `partial` 或 `unverified`，并一次提出最少的问题。
7. 只有附件或纯资料输入时，输出 `attachment-only`，保留 `challenge.yaml` 和高级资料。不要伪造服务入口。此类归档返回 `partial`。

## Flag 合同

普通题目默认使用 `direct-exec-v1`。平台直接把动态 Flag 写入程序实际读取的路径：

```yaml
flag:
  mode: direct_exec
  path: /var/www/html/flag.php
```

文件替换题和数据库题只记录真实业务更新方式：

```yaml
flag:
  mode: file_replace
  path: /flag.txt
  update:
    command: echo "$new_flag" > /flag.txt
```

数据库题可以在 `flag.update.wait_for` 中记录真实等待地址。只有题目真实需要等待服务时，才记录 `wait-for-it.sh`。

不要为 `direct_exec` 生成通用 `changeflag.sh`。`changeflag.sh` 只允许用于明确的 `helper_script`、旧平台兼容或 Linux-QEMU 合同。`start.sh` 不创建、覆盖或同步通用 Flag。

## 输出模式

| profile | 用途 | 行为 |
|---|---|---|
| `clean` | 默认新题目和半成品整理 | 生成简洁运行目录，移除明确的非运行文件 |
| `preserve` | 既有交付目录维护 | 保留目录语义，只修复明确合同问题 |
| `legacy` | 旧平台、旧 helper 和历史流程 | 允许 helper 和旧版报告文件 |

`profile` 不会把 `direct_exec` 变成 helper。输入包含 compose、Scenario、Bundle 或 Linux-QEMU 证据时，先报告路由结果。不要把多服务题目静默压成普通单服务题目。

## 验证结果

`inspect` 只读取事实。`scaffold` 只生成交付目录。`build` 只构建镜像。`verify` 才启动容器并检查运行入口、Flag 回读、声明的 solve probe 和可选 `smoke_assert.sh`。HTTP/TCP solve probe 会等待启动窗口并重试。

结果必须区分：

- `passed`：当前阶段的必要检查通过。
- `failed`：代码或交付合同失败。
- `partial`：部分证据通过，仍有未完成检查。
- `environment_failed`：Docker、架构或外部依赖阻塞。
- `not_reproduced`：没有执行足够的真实步骤。
- `unverified`：缺少必要事实，不能安全推断。

非 `direct_exec` Flag 模式没有执行题目专用更新命令时，不能报告为 `passed`。静态合同通过也不等于题目可解。

完成后用 5 到 10 行交付卡汇报：输出目录、源码根、启动命令、端口、Flag 模式和路径、已通过验证、未验证原因。

## 按需路由高级模式

只有输入证据或用户明确要求时，才读取对应资料：

| 触发条件 | 入口 | 资料 |
|---|---|---|
| 复杂历史题迁移 | `workflow.py` | `docs/legacy_migration.md`、`docs/orchestrated_workflow.md` |
| compose 或 Vulhub-like | `import_compose.py` → `render_scenario.py` | `data/scenario_schema.md` |
| Scenario 多服务编排 | `render_scenario.py`、`validate_scenario.py` | `docs/advanced_routing.md` |
| Bundle 或 BaseUnit | `render_bundle.py`、`render_component.py` | `docs/bundle_design.md` |
| RDG、AWD、AWDP、SecOps | `generate_check_stub.py`、`validate.sh` | `docs/validation_guide.md` |
| Linux kernel CVE/LPE | `render.py`、`linux_qemu_manual_check.sh` | `docs/linux_qemu_manual_validation.md` |
| 镜像归档和 amd64 交付 | `docker_artifacts.py` | `docs/advanced_routing.md` |

不要为了普通单服务题目读取全部高级资料。不要把仓库维护脚本当作题目构建入口。

## 资料索引

- `docs/core_contract.md`：默认输入、输出目录和交付卡格式。
- `docs/platform_contract_v3.md`：平台启动、Flag 和合同字段。
- `data/schema.md`：`challenge.yaml` 结构。
- `docs/stack_cookbook.md`：栈和运行时选择。
- `docs/validation_guide.md`：静态合同和业务入口验证。
- `docs/solve_probe_recipes.md`：HTTP、TCP 和 `container_exec` 断言。
- `docs/advanced_routing.md`：高级模式的触发条件和最小读取范围。

只读取当前任务需要的资料。详细模板、示例和仓库维护流程不属于默认上下文。
