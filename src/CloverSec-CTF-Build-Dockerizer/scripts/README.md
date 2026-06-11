# scripts 目录说明

职责边界：

- 仓库根目录 `scripts/` 负责发布治理与仓库级流程（如 `release_build.sh`、`publish_release.sh`、`doc_guard.sh`）。
- 本目录 `src/CloverSec-CTF-Build-Dockerizer/scripts/` 负责引擎运行链路（探测、渲染、校验、回归）。

## 脚本列表

- `render.py`：根据 challenge.yaml 或 CLI 参数渲染 Dockerfile/start.sh/changeflag.sh/flag(可选)
- `render_bundle.py`：根据固定 Bundle/Recipe 渲染单容器多服务交付目录
- `validate_bundle.py`：校验 Bundle/Recipe 渲染目录的结构与 recipe 契约
- `import_compose.py`：将 compose/Vulhub-like 输入转换为 scenario draft、renderable subset 和 import report
- `generate_check_stub.py`：生成 RDG/SecOps check-service 可编辑脚本骨架，默认带人工确认标记
- `workflow.py`：推荐工作流入口，依次完成题目分析、方案生成、确认、交付生成、验证和状态查看，并维护 `.ctfbuild/` 状态文件
- `audit_input.py`：输入审计，输出风险等级、推荐处理路径、支持等级、验证等级、是否需要人工确认和发现项
- `derive_config.py`：自动探测并输出 ProposedConfig（AI 编排模式专用）
- `parse_config_block.py`：解析方案确认 YAML（stdin）并生成标准 challenge.yaml
- `detect_stack.py`：输出技术栈侦测结果和置信度
- `validate.sh`：执行硬规则与可配置规则校验，支持 `--json-summary`
- `validate_scenario.py`：校验 scenario 输出，支持 `--validate-rendered` 和 `--format text|json`
- `autofix.py`：`validate.sh --fix/--fix-write` 对应的安全自动修复执行器
- `validate_examples.sh`：遍历 examples 全目录并做静态校验；默认只读执行，scenario 默认逐服务校验
- `smoke_test.sh`：执行 render/validate/build/run 冒烟回归；scenario 默认逐服务校验
- `test_runtime_profiles.sh`：运行时档位推断回归（php/node/java）
- `../../../scripts/validate_build_test.py`：校验仓库根目录 `Build_test/` 真实样例池，按 `cases.yaml` 做期望匹配
- `../../../scripts/linux_qemu_manual_check.sh`：Linux-QEMU release/manual 验证入口，默认只执行 preflight
- `../../../scripts/golden_snapshot.py`：渲染关键样例并与 `tests/golden/snapshots.json` 哈希清单对比
- `../../../scripts/platform_matrix.py`：采集当前主机、Docker、QEMU、SBOM 工具状态，输出跨平台矩阵结果
- `../../../scripts/generate_sbom.py`：生成 release SBOM；显式 `--strict` 时要求 syft 或 docker sbom 成功
- `../../../scripts/release_build.py`：发布打包入口；支持 `--sbom-strict` 进入 SBOM strict 模式
- `../../../scripts/publish_release.sh`：发布入口；可显式要求等待 GitHub Actions `release-full-check` 成功后再公开 Release
- `cleanup_test_containers.sh`：清理 `ctf-skill-test*` 容器和镜像
- `utils.py`：模板 include、变量渲染、推断与通用函数

## 常用命令

```bash
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/derive_config.py --project-dir .
```

```bash
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/workflow.py intake --project-dir .
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/workflow.py propose --project-dir .
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/workflow.py accept --project-dir .
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/workflow.py render --project-dir .
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/workflow.py validate --project-dir .
```

```bash
cat config-proposal.yaml | python3 src/CloverSec-CTF-Build-Dockerizer/scripts/parse_config_block.py --output challenge.yaml
```

```bash
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/render.py --config path/to/challenge.yaml
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/render.py --config path/to/challenge.yaml --format json
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/render_bundle.py --recipe legacy-centos7-python39-mysql57-redis5 --output /tmp/bundle
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/validate_bundle.py --bundle-dir /tmp/bundle
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/import_compose.py --compose docker-compose.yml --output /tmp/compose-import
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/generate_check_stub.py --type http --output check/check.sh --target-port 80 --path /
bash src/CloverSec-CTF-Build-Dockerizer/scripts/validate.sh --json-summary /tmp/validate-summary.json Dockerfile start.sh challenge.yaml
bash src/CloverSec-CTF-Build-Dockerizer/scripts/validate_examples.sh
bash src/CloverSec-CTF-Build-Dockerizer/scripts/smoke_test.sh
python3 scripts/validate_build_test.py
bash scripts/linux_qemu_manual_check.sh --mode preflight --case-dir /path/to/linux-qemu/code
python3 scripts/golden_snapshot.py
python3 scripts/platform_matrix.py --profile release
bash scripts/release_build.sh --with-smoke --sbom-strict
bash scripts/publish_release.sh --wait-release-full-check
```

校验规则详解见 `src/CloverSec-CTF-Build-Dockerizer/docs/validation_guide.md`。

Scenario 回归说明：

- 直接调用 `validate_scenario.py` 时，默认只校验 scenario/compose 结构。
- 追加 `--validate-rendered` 后，会对每个渲染出的服务目录调用 `validate.sh`。
- `validate_examples.sh` 和 `smoke_test.sh` 默认启用逐服务校验。
- 设置 `SCENARIO_VALIDATE_RENDERED=0` 可让批量回归只做 scenario/compose 结构校验。

Skill 入口文档说明：

- `SKILL.md` 只保留入口规则、路由表和按需读取索引。
- `doc_guard.sh` 会检查 `SKILL.md` 行数和关键入口，避免把 schema、栈手册、排障和命令细节重新塞回入口文件。
- `doc_guard.sh` 同时检查 `examples/README.md`、本脚本说明和 `agents/openai.yaml`，避免入口文档或 SkillHub metadata 漏掉确认门槛与治理脚本。

SBOM strict：

- 默认 SBOM 允许在 syft / docker sbom 不可用时退回 source-inventory。
- `generate_sbom.py --strict` 或 `release_build.py --sbom-strict` 会拒绝 fallback，适合审计要求更高的发布前检查。

GitHub Release 等待策略：

- `publish_release.sh --wait-release-full-check` 会在推送 `VERSION` tag 后轮询 GitHub Actions。
- 默认等待 `.github/workflows/ci.yml` 中名为 `release-full-check` 的 job 成功，再继续创建或公开 GitHub Release。
- 可用 `--release-full-check-timeout-seconds`、`--release-full-check-poll-seconds`、`--release-full-check-workflow`、`--release-full-check-job` 调整等待策略。
