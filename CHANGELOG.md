# 更新日志

本项目的重要变更都会记录在本文件中。

## v2.0.2 - 2026-03-06

### 变更

- README 体系重写为“中文默认 + 三语完整等价 + 中文兼容入口”：
  - `README.md`：中文默认完整手册
  - `README.en.md`：英文完整手册（不再是 legacy 短入口）
  - `README.ja.md`：日文完整手册
  - `README.zh-CN.md`：中文兼容入口（历史链接保留）
- 新增“版本演进叙事”并覆盖 `v1.5.0 -> v2.0.0 -> v2.0.1 -> v2.0.2` 全链路说明。
- 补齐并扩展高价值文档板块：
  - 一键安装与技能发现
  - Agent-Orchestrated 流程与 `CONFIG PROPOSAL` 确认门
  - AI 编程工具实战（Codex/Cursor/Trae/Claude Code/Copilot Chat/Aider）
  - 竞赛模式构建手册（Jeopardy/RDG/AWD/AWDP/SecOps/BaseUnit/Vulhub-like）
  - 文件级目录索引、FAQ、排障与发布验收清单
  - Workflow 截图与 Build_test 真实样例说明
- 移除三语 README 中的“参考资料”章节，改为仓库内文档与命令导航。
- `scripts/doc_guard.py` 增强 README 结构守卫：
  - 校验四个 README 文件存在与语言互链完整性
  - 校验关键章节存在（重点更新、AI 工具、模式手册、目录索引、FAQ）
  - 校验三份完整 README 的版本号与 `VERSION` 一致
  - 校验不再出现 `References/参考资料/参考` 章节
- `scripts/publish_guard.py` 新增发布前文档守卫：
  - 校验 README 资产完整性
  - 校验 `README.en.md` 非 legacy 短入口
  - 校验 `README.zh-CN.md` 为兼容入口并指向 `README.md`

### 发布

- 本版本为“文档与使用体验增强版”，不引入新的运行时行为变更。

## v2.0.1 - 2026-03-06

### 变更

- 补齐并固化 Vulhub-like 迁移示例：新增 `examples/scenario-vulhub-like-basic`，覆盖「challenge 来源 + component 来源」混合编排。
- 修复 `stacks.yaml` 重复定义风险：清理重复 `secops/baseunit`，并在 `utils.load_stack_defs` 对重复 stack id 直接报错，避免静默覆盖。
- 修复 AWDP 补丁包重复构建漂移：`patch_bundle.tar.gz` 改为确定性打包（固定 mtime/uid/gid 与排序）。
- 三语 README 与 `scenario_schema.md` 同步补充 Vulhub-like 示例命令与边界说明，强调 compose 仅用于本地编排，平台最终交付仍为单服务目录。

### 发布

- 该版本为 `v2.0.0` 收口补丁发布，保持接口与契约不变，仅做一致性收口与可重复构建修复。

## v2.0.0 - 2026-03-06

### 新增

- 新增 V2 交付契约：每次渲染默认产出 `Dockerfile`、`start.sh`、`changeflag.sh`，并在需要时产出 `flag` 与 `check/check.sh`。
- 新增 V2 配置主口径：`challenge.profile` 与 `challenge.defense`，覆盖 `jeopardy / rdg / awd / awdp / secops` 五类 profile。
- 新增独立技术栈：`secops`、`baseunit`。
- 新增 `data/profiles.yaml`，统一管理 profile 默认行为。
- 新增 `src/CloverSec-CTF-Build-Dockerizer/data/components.yaml` 与 `src/CloverSec-CTF-Build-Dockerizer/scripts/render_component.py`，支持指定组件和指定版本变体生成“纯服务包 / 纯基座镜像最小单元”。
- 新增 `src/CloverSec-CTF-Build-Dockerizer/data/scenario_schema.md`、`src/CloverSec-CTF-Build-Dockerizer/data/validate_scenario_rules.yaml`、`src/CloverSec-CTF-Build-Dockerizer/scripts/render_scenario.py`、`src/CloverSec-CTF-Build-Dockerizer/scripts/validate_scenario.py`，支持 AWD / AWDP / Vulhub-like 本地多服务场景编排与校验。
- 新增示例：
  - `examples/baseunit-redis-basic`
  - `examples/baseunit-sshd-basic`
  - `examples/secops-nginx-basic`
  - `examples/secops-nginx-hardening-basic`
  - `examples/secops-redis-hardening-basic`
  - `examples/node-awdp-basic`
  - `examples/scenario-awd-basic`
  - `examples/scenario-awdp-basic`
  - `examples/scenario-vulhub-like-basic`
- 新增日文完整文档：`README.ja.md`。
- 新增 `src/CloverSec-CTF-Build-Dockerizer/scripts/validate_context.py`，将 `validate.sh` 的 challenge 上下文解析逻辑稳定下沉到 Python。

### 变更

- `render.py` 升级到 V2 口径：
  - 支持 `profile` / `defense` / `secops` / `baseunit`
  - 强制生成 `/changeflag.sh`
  - 对 `awdp` 自动生成 `patch/src/`、`patch/patch.sh`、`patch_bundle.tar.gz`
  - 非 `rdg/secops` 栈可在 `profile!=jeopardy` 下复用 defense block
  - `patch_bundle.tar.gz` 改为确定性打包，避免重复回归触发二进制漂移
- `parse_config_block.py`、`derive_config.py` 升级为 V2 模型，兼容 legacy `challenge.rdg` 输入，但推荐输出 `challenge.defense`。
- `validate.sh` 升级：
  - `/changeflag.sh` 纳入硬规则
  - `profile` / `defense` / `secops` 场景进入统一门禁
  - 修复 challenge 上下文解析链路，消除嵌入式 Python 语法与兼容性问题
- `data/stacks.yaml` 去除重复 `secops/baseunit` 定义，`utils.load_stack_defs` 对重复 stack id 改为显式报错，避免静默覆盖。
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
