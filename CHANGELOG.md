# 更新日志

本项目的重要变更都会记录在本文件中。

## v1.5.0 - 2026-02-28

### 新增

- 新增运行时档位数据源：`src/CloverSec-CTF-Build-Dockerizer/data/runtime_profiles.yaml`（php/node/java）。
- 新增文档：
  - `src/CloverSec-CTF-Build-Dockerizer/docs/architecture_overview.md`
  - `src/CloverSec-CTF-Build-Dockerizer/docs/directory_guide.md`
- 新增治理脚本 Python 主实现：
  - `scripts/doc_guard.py`
  - `scripts/release_build.py`
  - `scripts/generate_sbom.py`
  - `scripts/sync.py`
  - `scripts/publish_guard.py`
- 新增运行时推断回归脚本：`src/CloverSec-CTF-Build-Dockerizer/scripts/test_runtime_profiles.sh`。

### 变更

- `derive_config.py` 增加运行时档位输出：`runtime_profile_candidates`、`recommended_profile`、`recommended_base_image`、`runtime_profile_evidence`。
- `render.py` 新增 `--runtime-profile`，并明确基础镜像优先级：`--base-image > --runtime-profile > challenge.base_image > infer/default`。
- `validate.sh` 增加 legacy 运行时告警（WARN，不阻断）：`php:5.6/7.4`、`node:14/16`、`temurin:8`（含 digest 形式）。
- 根目录治理 `.sh` 脚本改为 Python 兼容入口 wrapper，命令入口保持不变。
- `publish_release.sh` 维持编排角色，版本读取与白名单路径判定下沉到 `publish_guard.py`。
- `data/stacks.yaml` 与模板文档统一 Pwn 口径为 `xinetd/tcpserver/socat`。

### 文档

- `README.md` / `README.zh-CN.md` 升级到 `v1.5.0`，补充运行时兼容选择说明与 Python-first 治理脚本结构。
- `beginner_guide.md`、`platform_contract.md`、`troubleshooting.md` 修复与实现不一致描述（RDG flag 可选、9 栈口径、运行时兼容路径）。
- `SKILL.md` Step1 协议升级：Q1 明确“技术栈 + 运行时档位确认”（php/node/java）。

### CI

- `.github/workflows/ci.yml` 增加治理脚本 Python 入口自检（`--help`）。
- 增加 runtime profile 推断回归步骤，防止规则回退。

## v1.4.0-r2 - 2026-02-27

### 修复

- 修复 GitHub Actions `release-full-check` 中 `VERSION` 读取命令，解决 `tr: extra operand 'VERSION'` 导致的 SBOM 断言误失败。
- SBOM 断言步骤新增 `version` 非空检测，避免空值路径被误判通过。

### 文档

- `README.md` / `README.zh-CN.md`：
  - 版本与发布命令升级到 `v1.4.0-r2`
  - Pwn 启动能力口径统一为 `xinetd/tcpserver/socat`
  - 仓库结构补充 `scripts/generate_sbom.sh`
- `src/CloverSec-CTF-Build-Dockerizer/SKILL.md`：
  - “9 栈最小模板库索引”补齐 RDG 专节
  - Pwn 标题与描述升级为 `xinetd/tcpserver/socat`
- `src/CloverSec-CTF-Build-Dockerizer/docs/stack_cookbook.md`：
  - 目录与快速选型中的 Pwn 口径统一为 `xinetd/tcpserver/socat`
- `src/CloverSec-CTF-Build-Dockerizer/scripts/README.md`：
  - 新增 `autofix.py` 说明
  - 明确根目录 `scripts/` 与引擎 `src/.../scripts/` 职责边界

## v1.4.0-r1 - 2026-02-27

### 新增

- 新增模板组合片段：
  - `templates/snippets/docker-common-prolog.tpl`
  - `templates/snippets/docker-common-epilog.tpl`
  - `templates/snippets/run-bash-bootstrap.tpl`
- 新增 `validate.sh` 自动修复模式：
  - `--fix`（dry-run）
  - `--fix-write`（落盘）
  - `--fix-loopback`（显式允许 loopback 参数改写）
- 新增发布级基础镜像白名单：`data/base_image_allowlist.yaml`。
- 新增 SBOM 生成脚本：`scripts/generate_sbom.sh`（`syft` 优先，失败回退 `docker sbom`，兜底 placeholder）。
- 新增回归样例：
  - `examples/node-multiport-basic`
  - `examples/python-supervisor-basic`
  - `examples/pwn-socat-basic`
  - `examples/tomcat-context-basic`

### 变更

- 9 栈 Dockerfile 模板统一接入可组合横切层，减少重复模板逻辑，保留栈特有实现块。
- `pwn` 模板与校验升级为 `xinetd/tcpserver/socat` 三路径兼容。
- `smoke_test.sh` 新增每示例可选 `smoke_assert.sh` 自动断言入口。
- `release_build.sh` 在发布检查阶段启用 `VALIDATE_ENFORCE_DIGEST=1`，并自动产出 SBOM 与依赖清单资产。
- `publish_release.sh` 升级为多资产上传（zip + SPDX + CycloneDX + deps），保持 immutable-compatible 流程。
- CI 同步增强：
  - PR `fast-check` 新增 `validate --fix` dry-run 校验
  - tag/手动全检启用 digest 门禁
  - release-full-check 新增 SBOM 产物断言

### 验收要点

- `npx -y skills add . --list` 安装识别入口保持不变。
- 发布资产新增：
  - `CloverSec-CTF-Build-Dockerizer-v1.4.0-r1.zip`
  - `CloverSec-CTF-Build-Dockerizer-v1.4.0-r1.sbom.spdx.json`
  - `CloverSec-CTF-Build-Dockerizer-v1.4.0-r1.sbom.cdx.json`
  - `CloverSec-CTF-Build-Dockerizer-v1.4.0-r1.deps.txt`

## v1.4.0 - 2026-02-27

### 新增

- 新增 `challenge.healthcheck` 契约并落地渲染：支持 `enabled/cmd/interval/timeout/retries/start_period`，可在 Dockerfile 中生成可禁用的 `HEALTHCHECK`。
- 新增 `challenge.platform.allow_loopback_bind`（默认 `false`），用于 SSRF/内网链路题型显式放行 localhost 监听门禁。
- 新增推断与门禁字段：`derive_config.py` 输出 `gates.requires_explicit_stack_confirm`、`gates.requires_start_cmd_confirm`、`gates.requires_port_confirm`。
- 新增回归样例：
  - `examples/pwn-alpine-tcpserver-basic`
  - `examples/lamp-alpine-basic`
  - `examples/python-loopback-ssrf-basic`

### 变更

- `render.py`、`parse_config_block.py`、`schema.md` 全链路接入 healthcheck 与 loopback 配置解析。
- `pwn` 模板改为 Debian/Ubuntu + Alpine 双分支：Debian/Ubuntu 使用 `xinetd`，Alpine 使用 `tcpserver`（`ucspi-tcp6`）回退路径。
- `lamp` 模板改为 Debian/Ubuntu + Alpine 双分支：统一 Apache/PHP/MariaDB 安装并在 start 脚本中自动选择 `apache2ctl` 或 `httpd` 前台命令。
- `validate.sh` 工程化增强：
  - localhost/127.0.0.1 条件门禁（支持豁免与“公网前置+回环辅服务”INFO 放行）
  - 后台 `&` 启动后无前台阻塞进程的 ERROR 检测
  - 启动命令显式端口与 `EXPOSE`/`challenge.expose_ports` 一致性提示
  - Pwn 校验兼容 `xinetd` 与 `tcpserver`
- `patterns.yaml` 与 `utils.py` 增强内容匹配推断：
  - Python：FastAPI/Uvicorn、Poetry 信号
  - Node：NestJS、pnpm workspace、monorepo 结构
  - Java：Spring Boot 依赖与动态 JAR 路径（`target/*.jar`、`build/libs/*.jar`）
- `derive_config.py` 低置信/无入口路径加入“空启动候选 + 必填提示”，避免误生成误执行。

### 文档

- README（中英）同步到 `v1.4.0`，补充 healthcheck 落地、双分支运行时兼容、localhost 条件门禁与推断增强说明。
- `stack_cookbook.md`、`data/README.md`、`templates/README.md`、`SKILL.md` 同步更新新字段与新策略。

## v1.3.6-r1 - 2026-02-25

### 变更

- 收紧 `validate_rules.yaml` 中 AI 规则触发条件：`ai-thread-limit-recommended` 与 `ai-gunicorn-recommended` 仅在命中 `gunicorn|uvicorn|transformers` 时生效，避免 RDG/Python 普通场景误报。
- 强化 `smoke_test.sh` 的 PyYAML 依赖门禁：启动前必须可 `import yaml`，缺失时立即 `exit 2` 并输出安装指引，去除静默降级路径。
- 对齐 `doc_guard.sh` 与当前 README 版式：新增 `extract_readme_version()` 兼容 `VERSION:` / `VERSION：` / `<strong>VERSION</strong>:`，并把 Phase 检查调整为“仅在 README 启用 Phase 模板时执行”。

### 验证结果

- `bash -n`：`scripts/doc_guard.sh`、`src/CloverSec-CTF-Build-Dockerizer/scripts/smoke_test.sh` 通过。
- `python3 -m py_compile src/CloverSec-CTF-Build-Dockerizer/scripts/*.py` 通过。
- `validate_examples.sh` 与 `smoke_test.sh` 全量示例通过（18/18）。
- `rdg-python-ssti-basic` 在 `validate.sh` 下 AI 误报消失（`WARN=0`）。
- 模拟缺少 PyYAML 时，`smoke_test.sh` 按预期快速失败并返回 `exit 2`。

## v1.3.6 - 2026-02-25

### 新增

- 新增 RDG check 入口契约：`bash check/check.sh [target_ip] [target_port]`，支持 `TARGET_IP/TARGET_HOST/TARGET_PORT` 环境变量回退，统一返回码 `0/1/2` 语义。
- 新增 RDG 冒烟阶段 check 执行链路：`smoke_test.sh` 对 RDG 示例容器执行真实 `check/check.sh`。

### 变更

- `render.py` 的 RDG check 自动脚手架由 `TODO + exit 0` 改为 fail-closed（`CHECK_IMPLEMENT_ME + exit 1`），避免未实现脚本被误判为通过。
- `validate.sh` 在 `scoring_mode=check_service` 下新增占位脚本门禁：命中 `CHECK_IMPLEMENT_ME/TODO/placeholder` 或“短脚本 + exit 0”将直接报 `ERROR`。
- `examples/rdg-php-hardening-basic` 与 `examples/rdg-python-ssti-basic` 的 check 脚本改为真实检查实现（健康检查 + 漏洞负向检查）。
- RDG 示例业务基线同步为“默认已修复”状态，避免示例与检查逻辑自相矛盾。

### 文档与仓库治理

- README（中英主文）与 RDG 相关文档同步至 `v1.3.6`，补充 check 契约与 fail-closed 说明。
- `.gitignore` 新增 `check样例/`，明确参考目录不进入版本库。

## v1.3.5 - 2026-02-25

### 新增

- 新增 RDG 扩展配置字段：`enable_sshd`、`sshd_port`、`sshd_password_auth`、`ttyd_binary_relpath`、`ttyd_install_fallback`、`ctf_user`、`ctf_password`、`ctf_in_root_group`、`scoring_mode`、`include_flag_artifact`、`check_enabled`、`check_script_path`。
- 新增 RDG check-service 脚手架：`check/check.sh`（渲染时按需自动补齐）。
- 新增 RDG 样例 check 目录：`examples/rdg-php-hardening-basic/check/`、`examples/rdg-python-ssti-basic/check/`。

### 变更

- RDG 模板升级为 `ttyd + sshd` 双通道默认交付，默认创建 `ctf/123456`，可按题目配置覆盖。
- `render.py` 支持 RDG 端口自动补齐（业务端口 + sshd + ttyd），并支持 `include_flag_artifact=false` 无 flag 产物路径。
- RDG ttyd 回退链路增强：包管理安装不可用时自动尝试下载官方静态二进制并落地 `/ttyd`。
- `derive_config.py` 与 `parse_config_block.py` 输出/解析完整 RDG 配置模型。
- README（中英）与 RDG 文档更新为 v1.3.5 策略说明。

### 校验与兼容

- `validate.sh` RDG 检查升级为门禁级：`/ttyd`、sshd、ctf 口令初始化、root 组可选校验、check-service 脚本存在性。
- 当 `stack=rdg` 且 `include_flag_artifact=false` 时，放行 `/flag` 硬约束；其余栈规则不变。

### 仓库治理

- 版本升级至 `v1.3.5`，发布链路继续使用 immutable-compatible `publish_release.sh`。

## v1.2.4 - 2026-02-24

### 新增

- 新增独立中文文档：`README.zh-CN.md`。
- 新增 `README.en.md` 英文兼容入口页，用于承接历史外链。
- 新增 README 静态资源目录 `docs/assets/readme/`，并将流程截图全部本地化。

### 变更

- 将 `README.md` 切换为英文默认首页，并与中文文档保持信息等价。
- 在中文文档中重写 `What's New in v1.2.4`，补充首次公开发布的技术范围、Pwn/AI 适配与工程稳定性说明。
- 统一 README 中 License 指向为仓库内本地文件 `LICENSE`。

### 修复

- 修复历史模板链路中的报错描述与执行稳定性问题，覆盖渲染、校验与发布环节的关键路径。
- 修复 README 中本机绝对路径图片引用与外链图片依赖，改为仓库内相对路径资源。

### 安全 / 仓库治理

- 保持 `Build_test` 的业务可复现文件，同时移除会破坏仓库边界的元数据策略（嵌套 `.git`、`.DS_Store`）。
- 继续维持单一主工作目录与公开仓库边界，不回流敏感内部文件。

### 发布

- 版本号保持 `v1.2.4`。
- `publish_release.sh` 持续作为完整发布入口（commit/tag/release/资产上传）。

## v1.2.3 - 2026-02-24

### 新增

- 新增双语 README 布局（中文主文 + 英文文档）。
- 新增 `CHANGELOG.md` 作为稳定的版本变更入口。
- 新增 GitHub Releases 的文档入口链接。

### 变更

- 将 README 改写为面向公开发布的标准化结构：范围清晰、安装路径清晰、平台约束清晰。

### 说明

- 本版本主要聚焦文档与发布展示层改造。
- 核心渲染与校验行为保持不变。

## v1.2.2 - 2026-02-24

### 新增

- 新增文档治理脚本：`scripts/doc_guard.sh`。
- 新增可审计的阶段性回填内容。

### 变更

- 将 `doc_guard.sh` 集成到 `scripts/release_build.sh`。
- 强化发布前文档校验约束。

### 修复

- 清理失效文档引用与缺失路径链接。
- 统一公开文档命名策略。

## v1.2.1 - 2026-02-24

### 变更

- 更新 `SKILL.md` 前置信息描述，使其更准确覆盖 Jeopardy（Web/Pwn/AI）范围。
- 扩展 `argument-hint`，覆盖 8 种受支持栈。

## v1.2.0 - 2026-02-24

### 新增

- 完成项目重命名为 `CloverSec-CTF-Build-Dockerizer`。
- 新增 `pwn` 与 `ai` 栈支持（模板、规则、示例、回归）。
- 强制发布产物命名与根目录 `VERSION` 对齐。

### 变更

- 发布打包结构统一为单目录 zip 形态。
- `dist` 命名与发布结构标准化，提升可追溯性。

### 说明

- 作用域仍为 Jeopardy 题型；AWD/AWDP 不在本项目范围内。
