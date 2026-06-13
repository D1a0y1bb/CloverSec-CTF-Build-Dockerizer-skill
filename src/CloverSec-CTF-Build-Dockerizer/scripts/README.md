# scripts 目录说明

职责边界：

- 本目录 `scripts/` 只负责题目构建链路：探测、提案、渲染、校验和 Linux-QEMU 手动检查。

## 脚本列表

- `render.py`：根据 challenge.yaml 或 CLI 参数渲染 Dockerfile/start.sh/changeflag.sh/flag(可选)
- `render_bundle.py`：根据固定 Bundle/Recipe 渲染单容器多服务交付目录
- `validate_bundle.py`：校验 Bundle/Recipe 渲染目录的结构与 recipe 契约
- `import_compose.py`：将 compose/Vulhub-like 输入转换为 scenario draft、renderable subset 和 import report
- `generate_check_stub.py`：生成 RDG/SecOps check-service 可编辑脚本骨架，默认带人工确认标记
- `workflow.py`：推荐工作流入口，依次完成题目分析、方案生成、确认、交付生成、验证和状态查看，并记录 `.ctfbuild/` 状态文件
- `audit_input.py`：输入审计，输出风险等级、推荐处理路径、支持等级、验证等级、是否需要人工确认和发现项
- `derive_config.py`：自动探测并输出 ProposedConfig（AI 编排模式专用）
- `parse_config_block.py`：解析方案确认 YAML（stdin）并生成标准 challenge.yaml
- `detect_stack.py`：输出技术栈侦测结果和置信度
- `render_scenario.py`：渲染多服务本地编排；用户确认后使用 `--accepted --reason`
- `validate.sh`：执行硬规则与可配置规则校验，支持 `--json-summary`、`--static-only` 和动态 flag 校验层级标记
- `validate_scenario.py`：校验 scenario 输出，支持 `--validate-rendered` 和 `--format text|json`
- `smoke_test.sh`：构建并启动指定示例，执行 `challenge.verification.solve_probe` 或 `smoke_assert.yaml` 里的业务入口断言
- `autofix.py`：`validate.sh --fix/--fix-write` 对应的安全自动修复执行器
- `linux_qemu_manual_check.sh`：Linux-QEMU guest 启动、guest flag 和 PoC 验证入口，默认只执行 preflight
- `verify_asset_manifest.py`：校验 Linux-QEMU 外部 VM 资产 manifest 的文件存在、大小和 SHA256
- `docker_artifacts.py`：生成 Docker build/run/save/load/import 计划，执行选定步骤，并输出 `environment`、`docker_artifacts`、`xlsx_fields`
- `utils.py`：模板 include、变量渲染、推断与通用函数

## 常用命令

```bash
python3 scripts/derive_config.py --project-dir .
```

确认前：

```bash
python3 scripts/workflow.py intake --project-dir .
python3 scripts/workflow.py propose --project-dir .
python3 scripts/workflow.py status --project-dir .
```

`workflow.py --pretty status` 和 `workflow.py status --pretty` 都会输出 JSON，等价于 `--format json`。

用户确认方案后：

```bash
python3 scripts/workflow.py accept --project-dir .
python3 scripts/workflow.py render --project-dir .
python3 scripts/workflow.py validate --project-dir .
```

低风险且已有明确 `challenge.yaml` 时，熟练用户可用快速审查入口。该入口仍要求写明原因；mixed/dirty/high_risk 输入或未接受 proposal 的高风险输入会被拒绝：

```bash
python3 scripts/workflow.py reviewed-render --project-dir . --reason "reviewed explicit challenge.yaml"
```

接受后如人工修改了 `challenge.yaml`，使用下面命令登记当前配置，不重新生成文件：

```bash
python3 scripts/workflow.py accept --project-dir . --refresh --notes "reviewed manual edits"
```

```bash
cat config-proposal.yaml | python3 scripts/parse_config_block.py --output challenge.yaml
```

```bash
python3 scripts/render.py --config path/to/challenge.yaml
python3 scripts/render.py --config path/to/challenge.yaml --format json
python3 scripts/render_bundle.py --recipe legacy-centos7-python39-mysql57-redis5 --output /tmp/bundle
python3 scripts/validate_bundle.py --bundle-dir /tmp/bundle
python3 scripts/import_compose.py --compose docker-compose.yml --output /tmp/compose-import
python3 scripts/generate_check_stub.py --type http --output check/check.sh --target-port 80 --path / --expect-status 200
bash scripts/validate.sh --json-summary /tmp/validate-summary.json Dockerfile start.sh challenge.yaml
bash scripts/validate.sh --static-only Dockerfile start.sh challenge.yaml
bash scripts/smoke_test.sh --case python-flask-basic
bash scripts/linux_qemu_manual_check.sh --mode preflight --case-dir /path/to/linux-qemu/code --asset-manifest /path/to/asset_manifest.yaml
python3 scripts/verify_asset_manifest.py --manifest /path/to/asset_manifest.yaml
python3 scripts/docker_artifacts.py plan --project-dir . --image-name cloversec/example:latest --tar-path archive/example.tar --port 18080:80 --output docker_artifacts.json
```

校验规则详解见 `docs/validation_guide.md`。

Scenario 说明：

- 直接调用 `validate_scenario.py` 时，默认只校验 scenario/compose 结构。
- 追加 `--validate-rendered` 后，会对每个渲染出的服务目录调用 `validate.sh`。
- `render_scenario.py` 用户侧调用时，必须在用户确认服务清单和端口摘要后传入 `--accepted --reason "..."`。
- `import_compose.py` 会在 draft 中保留 ports、environment、depends_on、volumes、networks、healthcheck、command/entrypoint 等线索；只有能安全转换的服务会进入 renderable subset。
- 由 Compose 导入的 `depends_on` 会被 `render_scenario.py` 写回 `docker-compose.yml`，并由 `validate_scenario.py` 校验依赖目标是否存在。

check-service 生成器说明：

- HTTP 支持 `--expect-status`、`--expect-text`、`--forbid-text`、`--expect-header`、`--forbid-header`。
- Redis 支持 `--redis-key` 和 `--redis-expect-value`。
- MySQL 支持 `--mysql-query` 和 `--mysql-expect-text`。
- SSH 支持 `--ssh-expect-banner`。
- 生成脚本默认带 `CHECK_REVIEW_REQUIRED`，人工确认健康检查和业务断言后才能移除。

Validate 分层说明：

- 默认 `validate.sh` 执行静态契约检查和动态 flag 写入检查，并在 `--json-summary` 中写入 `verification.level=contract+dynamic-flag`。
- `validate.sh` 不证明题目业务可解；需要题目入口验证时，在 `challenge.verification.solve_probe` 或 `smoke_assert.yaml` 中写 HTTP/TCP/container_exec 断言，再执行 `bash scripts/smoke_test.sh --case <example-name>`。
- 内置 `python-flask-basic` 已包含 `challenge.verification.solve_probe`，可用 `bash scripts/smoke_test.sh --case python-flask-basic` 直接验证该字段会被读取并执行。
- 常用 HTTP/TCP/container_exec/Pwn nc 断言片段见 `docs/solve_probe_recipes.md`。
- `challenge.flag.sync_paths` 由生成的 `/changeflag.sh` 同步。若平台只覆盖 `/flag` 后直接启动服务，业务路径不会自动得到动态 flag；只有用户明确说明平台不会调用 `/changeflag.sh` 时，才把启动时同步写成题目特定兼容逻辑。
- `--static-only` 只做静态契约检查，适合快速检查 Dockerfile/start.sh/challenge.yaml。
- 核心校验脚本按 `0=通过、1=契约失败、2=配置/路径/环境错误` 返回。
- Linux-QEMU boot、guest flag 写入和 PoC 复现使用 `linux_qemu_manual_check.sh`，默认不会在快速校验里自动执行。

Docker artifact 说明：

- 默认平台为 `linux/amd64`，计划中的 `docker build` 使用 `--platform linux/amd64`。
- `plan` 只生成命令和元数据，不执行 Docker。
- `execute` 会执行计划里的指定步骤，例如 `build,run,save_image_tar,inspect_image`。
- `validate-artifacts` 可读取 `docker image inspect` 导出的 JSON，并检查平台是否等于 `linux/amd64`。
- image tar 使用 `docker save` / `docker load`；如传入 `--container-tar-path`，同时生成 `docker export` / `docker import` 命令。
