# 更新日志

本项目的重要变更都会记录在本文件中。

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
