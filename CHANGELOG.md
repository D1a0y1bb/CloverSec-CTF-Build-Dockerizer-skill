# 更新日志

本项目的重要变更都会记录在本文件中。

## v2.0.0 - 2026-03-06

### 新增

- 新增 V2 交付契约：每次渲染默认产出 `Dockerfile`、`start.sh`、`changeflag.sh`，并在需要时产出 `flag` 与 `check/check.sh`。
- 新增 V2 配置主口径：`challenge.profile` 与 `challenge.defense`，覆盖 `jeopardy / rdg / awd / awdp / secops` 五类 profile。
- 新增独立技术栈：`secops`、`baseunit`。
- 新增 `data/profiles.yaml`，统一管理 profile 默认行为。
- 新增 `data/components.yaml` 与 `scripts/render_component.py`，支持指定组件和指定版本变体生成“纯服务包 / 纯基座镜像最小单元”。
- 新增 `data/scenario_schema.md`、`data/validate_scenario_rules.yaml`、`scripts/render_scenario.py`、`scripts/validate_scenario.py`，支持 AWD / AWDP / Vulhub-like 本地多服务场景编排与校验。
- 新增示例：
  - `examples/baseunit-redis-basic`
  - `examples/baseunit-sshd-basic`
  - `examples/secops-nginx-basic`
  - `examples/secops-nginx-hardening-basic`
  - `examples/secops-redis-hardening-basic`
  - `examples/node-awdp-basic`
  - `examples/scenario-awd-basic`
  - `examples/scenario-awdp-basic`
- 新增日文完整文档：`README.ja.md`。
- 新增 `scripts/validate_context.py`，将 `validate.sh` 的 challenge 上下文解析逻辑稳定下沉到 Python。

### 变更

- `render.py` 升级到 V2 口径：
  - 支持 `profile` / `defense` / `secops` / `baseunit`
  - 强制生成 `/changeflag.sh`
  - 对 `awdp` 自动生成 `patch/src/`、`patch/patch.sh`、`patch_bundle.tar.gz`
  - 非 `rdg/secops` 栈可在 `profile!=jeopardy` 下复用 defense block
- `parse_config_block.py`、`derive_config.py` 升级为 V2 模型，兼容 legacy `challenge.rdg` 输入，但推荐输出 `challenge.defense`。
- `validate.sh` 升级：
  - `/changeflag.sh` 纳入硬规则
  - `profile` / `defense` / `secops` 场景进入统一门禁
  - 修复 challenge 上下文解析链路，消除嵌入式 Python 语法与兼容性问题
- `smoke_test.sh` 与 `validate_examples.sh` 增强：
  - 识别 `scenario.yaml`
  - 调用 `render_scenario.py` / `validate_scenario.py`
  - `check_service` 不再只绑定 `rdg`，而是按 `profile + scoring_mode + check_enabled` 泛化执行
- `render_component.py` 改为把 `challenge.yaml` 持久写入输出目录，便于 `scenario` 二次覆盖与再渲染。

### 文档

- `README.md` / `README.zh-CN.md` / `README.ja.md` 统一升级到 `v2.0.0`，补齐：
  - 多语言导航
  - `profile / defense / secops / baseunit / scenario / changeflag`
  - 平台最终交付与本地 compose 编排边界
  - baseunit 组件生成器用法
  - AWDP 补丁包工作流
  - AWD 与 secops 的差异
- `SKILL.md`、`schema.md`、`platform_contract.md`、`architecture_overview.md`、`directory_guide.md`、`stack_cookbook.md`、`data/README.md`、`templates/README.md` 同步到 V2 口径。

### 发布与兼容

- 对外安装入口保持不变：`npx -y skills add ... --skill cloversec-ctf-build-dockerizer`
- Release 继续采用 immutable-compatible 流程。
- 仍保留 `README.en.md` 作为历史英文兼容入口。

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
