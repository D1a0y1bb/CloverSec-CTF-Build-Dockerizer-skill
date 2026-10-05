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

# CloverSec CTF Build Dockerizer

## 默认任务

把题目想法、半成品源码、参考目录或历史交付件整理为干净、可读、可构建、可验证的 CTF 容器目录。

默认交付目标是：

```text
challenge/
├── src/                         # 题目运行源码或二进制
├── Dockerfile                   # 镜像构建入口
├── start.sh                    # 真实服务启动入口
├── challenge.yaml              # 最小平台合同
├── .dockerignore                # 排除机器报告和附件
└── flag                       # 仅启动前需要初始文件时保留
```

普通题目默认不生成 `changeflag.sh`、`FLAG_UPDATE.md`、`VERIFY.md` 或根目录 `delivery-manifest.json`。

机器审计、验证和归档信息放在输出目录的 `.ctfbuild/`，发布归档放在 `dist/`。这些目录不属于题目运行源码。

保留用户的原始输入。默认输出到 `<题目目录>/dist` 或用户指定的独立目录，不覆盖原始源码。

## 默认入口

本文中的 `scripts/`、`docs/`、`data/`、`templates/`、`examples/` 都相对于本 `SKILL.md` 所在目录。使用已安装 Skill 时，先解析 Skill 根目录，不要添加源码仓库前缀。

输入可以是题目目录，也可以是 `challenge.yaml` 所在目录：

```bash
python3 scripts/ctfctl.py inspect --project-dir <题目目录> --format json
python3 scripts/ctfctl.py scaffold --project-dir <题目目录> --output <题目目录>/dist --profile clean
python3 scripts/ctfctl.py verify --project-dir <题目目录>/dist --format json
python3 scripts/ctfctl.py package --project-dir <题目目录>/dist --output <题目目录>/challenge.tar.gz
```

`audit` 等价于 `inspect`。`prepare` 等价于 `scaffold`。

默认顺序是：读取事实、整理目录、生成最小入口、执行静态合同检查、执行可用的 Docker 验证、输出简短交付卡。

## 输入和源码规则

- 先读取已有 `Dockerfile`、`start.sh`、`challenge.yaml`、源码入口、依赖文件和题目手册中的启动事实。
- 已有 Dockerfile 或启动脚本时，优先保留其运行语义，再修复明确的交付合同问题。
- 只有附件或纯资料题目可以输出 `attachment-only`，不要伪造服务入口。
- 新生成的服务源码使用 `src/`。已有目录结构能解释运行方式时，保留已有结构。
- 删除缓存、压缩包、题目手册、附件和旧 `dist` 时，只删除明确不属于运行时的文件。
- 不把 `README`、长篇教程注释或发布报告写入普通题目根目录，除非用户明确要求。
- 缺少端口、启动命令、运行时或真实 Flag 路径时，不猜测业务配置。输出 `partial` 或 `unverified`，并一次性提出最少的问题。

## Flag 合同

普通题目默认使用 `direct-exec-v1`：平台直接写入 `challenge.flag.path`。

```yaml
flag:
  mode: direct_exec
  path: /var/www/html/flag.php
```

`/flag` 只是默认值。必须根据源码、Dockerfile 或题目手册设置程序实际读取的路径。

文件替换题和数据库题只把真实业务更新方式写入 `flag.update`：

```yaml
flag:
  mode: file_replace
  path: /var/www/html/flag.php
  update:
    command: sed -i "s/$flag/$new_flag/g" /var/www/html/flag.php
```

数据库题可以在 `flag.update.wait_for` 中记录服务等待地址。只有题目真实需要等待服务时，才使用 `wait-for-it.sh`。

不要为 direct-exec 生成通用 `changeflag.sh`。`changeflag.sh` 只允许用于明确的 `helper_script`、旧平台兼容或 Linux-QEMU 合同。

`start.sh` 不创建、覆盖或同步通用 Flag。单服务入口使用 `exec` 启动真实前台服务。

## 输出 profile

| profile | 用途 | 根目录附加文件 |
|---|---|---|
| `clean` | 默认新建题目和半成品整理 | 不生成机器报告 |
| `preserve` | 保留既有交付目录语义 | 只修复明确合同问题 |
| `legacy` | 旧平台、旧 helper 或历史流程 | 允许生成旧版报告文件 |

所有 profile 都遵守真实 Flag 路径。profile 不会把 direct-exec 变成 helper。

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

不要为了普通单服务题目读取全部高级资料。不要把 Release 脚本当作题目构建入口。

## 验证和汇报

`inspect` 只读取输入事实。`scaffold` 只生成交付目录。`verify` 才尝试 Docker build、run、Flag 写入和题目入口探测。

结果必须区分：

- `passed`：当前阶段的必要检查通过。
- `failed`：代码或交付合同失败。
- `partial`：部分证据通过，仍有未完成检查。
- `environment_failed`：Docker、架构或外部依赖阻塞。
- `not_reproduced`：没有执行足够的真实步骤。
- `unverified`：缺少必要事实，不能安全推断。

不要把静态合同通过说成题目可解。不要把未执行的 Docker、QEMU 或业务入口检查说成已验证。

完成后用 5 到 10 行交付卡汇报：输出目录、源码根、启动命令、端口、Flag 模式和路径、已通过验证、未验证原因。

## 资料索引

- `docs/core_contract.md`：默认输入、输出目录和交付卡格式。
- `docs/platform_contract_v3.md`：平台启动、Flag 和合同字段。
- `data/schema.md`：`challenge.yaml` 结构。
- `docs/stack_cookbook.md`：栈和运行时选择。
- `docs/validation_guide.md`：静态合同和业务入口验证。
- `docs/solve_probe_recipes.md`：HTTP、TCP 和 `container_exec` 断言。
- `docs/advanced_routing.md`：高级模式的触发条件和最小读取范围。

只读取当前任务需要的资料。详细模板、示例和发布流程不属于默认上下文。
