# 更新日志

本项目的重要变更都会记录在本文件中。

## Unreleased

### 新增

- `Build_test/` 升级为真实样例池，新增 `cases.yaml`、每个样例的 `case_note.md` 和独立说明文档。
- 新增 `scripts/validate_build_test.py`，按 `cases.yaml` 对真实样例执行输入审计与 Docker 契约期望匹配，支持 `--format json`、`--case` 和 `--fail-fast`。
- 首批样例覆盖现有历史样例、cPanel/WHM 仿真、Linux-QEMU 缺资产、Web 历史题、Pwn compose/xinetd 输入和 PHP compose 输入。
- 新增 Linux-QEMU release/manual 验证套件：`linux_qemu_manual_validation.md`、`scripts/linux_qemu_manual_check.sh` 和真实 Fragnesia 外部资产记录。
- 新增 Bundle/Recipe 原型，提供两个固定组合、`render_bundle.py`、`validate_bundle.py`、schema、设计文档和输入示例。
- 新增 compose import draft：`import_compose.py` 输出 `scenario.draft.yaml`、`scenario.renderable.yaml` 与 `import-report.json`，并提供导入示例。
- 新增 `generate_check_stub.py`，支持 HTTP/TCP/Redis/MySQL/SSH check-service 可编辑骨架。

### 变更

- `validate.sh` 的 Linux-QEMU debugfs 检测支持 `sif` 别名，避免真实 `changeflag.sh` 被误判为没有写入 guest rootfs。
- `validate_examples.sh` 识别 `bundle.yaml`，在临时目录渲染并校验 Bundle 示例，保持 examples 只读。
- `validate_examples.sh` 识别 compose 示例，默认校验导入后的可渲染 Scenario 子集。
- `validate.sh` 将 `CHECK_REVIEW_REQUIRED` 视为未确认 check-service 标记，继续阻断发布。

## v2.1.2 - 2026-06-10

### 新增

- 新增 `workflow.py` 推荐入口，提供 `intake / propose / accept / render / validate / status` 命令，并在题目目录维护 `.ctfbuild/session.json`、proposal 与 accepted proposal 状态文件。
- 新增 `audit_input.py` 输入审计，输出 `risk_level`、`recommended_path`、`support_level`、`verification_level`、`manual_required` 与 `findings[]`；`derive_config.py` 的 JSON/YAML 输出同步携带 `input_audit`。
- `render.py` 新增 Proposal Gate、`--format text|json`、`--manual --reason`。混合输入、脏目录、高风险输入或 derive gates 为 true 时，默认要求 accepted proposal。
- `validate.sh` 新增 `--json-summary <path>`，`validate_scenario.py` 新增 `--format text|json`，失败结果可稳定输出结构化错误码。

### 变更

- `validate_context.py` 在传入 `challenge.yaml` 后如遇文件缺失、PyYAML 缺失或 YAML 解析失败，会返回非 0，并统一归类为 `CONFIG_CONTEXT_PARSE_FAILED`。
- 发布检查升级：`release_build.py` 支持 `--with-smoke`、SkillHub metadata 检查、当前版本 CHANGELOG 标题检查、`agents/` 打包检查、SBOM 来源记录和 `release-status.json`。
- `publish_release.sh` 正式发布默认执行 Docker smoke；如需跳过必须传入 `--skip-smoke-with-reason "..."`。找不到当前版本 release notes 时发布失败。

### 发布

- 本版本聚焦工作流门槛、输入审计、结构化错误与发布前检查，不扩展样例池，不引入 Bundle/Recipe 或 Scenario import，也不重写 `SKILL.md` 主体。

## v2.1.1 - 2026-06-10

### 修复

- 修复 `SKILL.md` frontmatter `name` 不符合 SkillHub slug 规则的问题，发布包现在使用 `cloversec-ctf-build-dockerizer`。
- 移除 `SKILL.md` 中会触发内部 Git 导出 `diff --check` 失败的行尾空格。
- 发布构建增加 SkillHub slug 与行尾空格检查，提前拦截会导致同步失败的包内容。
- 三语 README 增加 `v2.1.1` 发布修复说明，公开 docs 标题同步到当前版本。
- 文档检查增加当前版本说明章节检查，避免只更新顶部版本号而遗漏正文说明。

## v2.1.0 - 2026-06-10

### 新增

- 新增 `linux-qemu` 技术栈，面向 Linux kernel CVE/LPE 题目：外层 Docker 镜像启动 QEMU，内层 guest 承载指定 vulnerable kernel、initrd/rootfs。
- 新增 `challenge.vm` 配置，覆盖 QEMU binary、arch、TCG/KVM、kernel/initrd/rootfs、hostfwd、guest flag 路径和 flag 注入方式。
- 新增 `templates/linux-qemu/` 与 `examples/linux-qemu-basic/`，轻量示例用于 render/validate，不携带可启动大型 VM 资产。

### 变更

- `render.py` 支持把 `challenge.vm` 渲染为结构化 QEMU 启动脚本，并为 `linux-qemu` 生成可写 guest rootfs 的 `changeflag.sh`。
- `derive_config.py`、`parse_config_block.py`、`data/stacks.yaml`、`data/patterns.yaml` 同步支持 `linux-qemu`。
- `validate.sh` 增加 QEMU 专项检查：QEMU 依赖、`-nographic`、`hostfwd`、monitor/gdbstub 风险、VM 资产、KVM 要求、guest flag 路径、EXPOSE 与 hostfwd 一致性。
- `smoke_test.sh` 增加 `LINUX_QEMU_RUN_MODE=validate-only|build-only|full`，默认仅做 render/validate。
- `linux-qemu` 渲染增加 VM 字段字符级校验、TCP-only guest forward、`healthcheck_mode` 默认命令映射与 aarch64 QEMU 包校验。
- release 打包跳过 Git ignored 文件，SBOM 工具不可用时生成源码清单型 SBOM，并阻止打包校验阶段改写源目录。

### 发布

- 完整 QEMU boot、PoC 复现、真实动态 flag 注入仍属于 release/manual 级验证；默认回归不启动占位 VM 示例。

## v2.0.3-r1 - 2026-03-06

### 变更

- 新增 `src/CloverSec-CTF-Build-Dockerizer/agents/openai.yaml`，用于 Codex UI 中的 Skill 卡片展示、短描述与默认提示词配置。
- `src/CloverSec-CTF-Build-Dockerizer/SKILL.md` 顶部说明结构前移，采用 `一句话定位 / 能力边界 / 适用场景 / 注意事项` 的前置展示方式，便于在技能详情页中直接阅读。
- `README.md` 追加 `v2.0.3-r1` 补充说明，并同步三语 README 顶部版本号到 `v2.0.3-r1`。

### 发布

- 本版本为展示层与文档收口发布，不引入 `render.py`、`validate.sh`、`render_component.py`、`render_scenario.py` 等运行时逻辑变更。

## v2.0.3 - 2026-03-06

### 变更

- 修复三语 README 的历史错链，统一当前文档入口为：`README.md`（中文默认）、`README.en.md`（英文完整）、`README.ja.md`（日文完整）。
- 收敛 README 中过强或易过时的承诺性表述，改为以“当前已验证能力范围”和“兼容优先迭代”描述项目边界。
- 将 `beginner_guide.md` 升级到 V2 口径，补齐 `changeflag.sh`、`secops`、`baseunit`、`scenario`、`awd`、`awdp` 等能力说明。
- 修正文档契约错位：
  - `changeflag.sh` 明确为硬产物
  - `/flag` 明确为条件产物
  - `challenge.yaml` 不再被表述为所有渲染路径都必然重新输出的硬产物
- 更新 `directory_guide.md`、`SKILL.md`、`platform_contract.md`、`architecture_overview.md`、`stack_cookbook.md`、`data/README.md`，统一到当前实现语义。
- `scripts/doc_guard.py` 收口到当前三语 README 结构，不再强依赖已删除的历史中文入口文件。

### 发布

- 本版本为纯文档一致性修复，不引入新的运行时功能。

## v2.0.2 - 2026-03-06

### 变更

- README 体系重写为“中文默认 + 三语完整等价文档”
  - `README.md`：中文默认完整手册
  - `README.en.md`：英文完整手册（不再是 legacy 短入口）
  - `README.ja.md`：日文完整手册
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
  - 校验三份完整 README 存在与语言互链完整性
  - 校验关键章节存在（重点更新、AI 工具、模式手册、目录索引、FAQ）
  - 校验三份完整 README 的版本号与 `VERSION` 一致
  - 校验不再出现 `References/参考资料/参考` 章节
- `scripts/publish_guard.py` 新增发布前文档守卫：
  - 校验 README 资产完整性
  - 校验 `README.en.md` 非 legacy 短入口

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

- `README.md` / `README.en.md` / `README.ja.md` 统一升级到 `v2.0.0`，补齐：
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
