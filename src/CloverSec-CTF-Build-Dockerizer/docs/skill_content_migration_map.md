# SKILL.md 渐进加载迁移映射

本文档记录 P1.8 把旧版 `SKILL.md` 长内容迁出后的归属位置，便于审查“内容是否还在”。

旧版基线：`29d470e:src/CloverSec-CTF-Build-Dockerizer/SKILL.md`，共 1089 行。
新版入口：`src/CloverSec-CTF-Build-Dockerizer/SKILL.md`，控制在 500 行以内。

## 迁移总览

| 旧章节 | 当前位置 | 状态 |
|---|---|---|
| 一句话定位 / 能力边界 / 适用场景 | `SKILL.md` 的任务定位、必须遵守、输入路由 | 保留为短入口 |
| 注意事项 / 平台硬约束 | `SKILL.md`、`src/CloverSec-CTF-Build-Dockerizer/docs/platform_contract.md`、`src/CloverSec-CTF-Build-Dockerizer/docs/validation_guide.md` | 保留并分层 |
| 快速开始 / 文档导航 | `SKILL.md`、`src/CloverSec-CTF-Build-Dockerizer/scripts/README.md`、`src/CloverSec-CTF-Build-Dockerizer/docs/beginner_guide.md` | 保留为入口和命令索引 |
| 白皮书章节映射 | `README.md` 和各 docs 索引 | 不再在 Skill 入口重复 |
| 输入契约字段表 | `src/CloverSec-CTF-Build-Dockerizer/data/schema.md` | 已承接 |
| RDG/Defense check 脚本契约 | `src/CloverSec-CTF-Build-Dockerizer/docs/validation_guide.md` | 已承接 |
| 统一模板变量清单 | `src/CloverSec-CTF-Build-Dockerizer/docs/validation_guide.md` | 已补入 |
| validate 自动修复与发布门禁 | `src/CloverSec-CTF-Build-Dockerizer/docs/validation_guide.md` | 已承接 |
| 平台契约解释 | `src/CloverSec-CTF-Build-Dockerizer/docs/platform_contract.md` | 已承接 |
| AI Orchestrated Mode 强制协议 | `src/CloverSec-CTF-Build-Dockerizer/docs/orchestrated_workflow.md`，`SKILL.md` 保留硬门槛 | 已补入 |
| 手动模式 | `src/CloverSec-CTF-Build-Dockerizer/scripts/README.md`、`src/CloverSec-CTF-Build-Dockerizer/docs/beginner_guide.md` | 已承接 |
| 12 栈最小模板库索引 | `src/CloverSec-CTF-Build-Dockerizer/docs/stack_cookbook.md` | 已补入 |
| validate 规则速查 | `src/CloverSec-CTF-Build-Dockerizer/docs/validation_guide.md` | 已承接 |
| 输出契约清单 | `src/CloverSec-CTF-Build-Dockerizer/docs/validation_guide.md`、`src/CloverSec-CTF-Build-Dockerizer/docs/platform_contract.md` | 已承接 |
| 故障排查剧本 | `src/CloverSec-CTF-Build-Dockerizer/docs/troubleshooting.md` | 已承接 |
| 命令速查 | `src/CloverSec-CTF-Build-Dockerizer/scripts/README.md` | 已承接 |
| 对 LLM/Agent 工具的执行要求 | `SKILL.md` 输出汇报要求、`src/CloverSec-CTF-Build-Dockerizer/docs/orchestrated_workflow.md` | 已承接 |
| 对维护者的执行要求 | `CHANGELOG.md`、`scripts/doc_guard.py`、`src/CloverSec-CTF-Build-Dockerizer/scripts/README.md` | 已承接 |
| 自检清单 | `src/CloverSec-CTF-Build-Dockerizer/docs/validation_guide.md` 发布前检查 | 已承接 |
| 变更边界 | `SKILL.md` 任务定位和输入路由 | 保留为短入口 |
| 相关文件索引 | `SKILL.md` 按需读取索引、`README.md` 文件目录索引 | 已承接 |
| 附录 A/B 命令 | `src/CloverSec-CTF-Build-Dockerizer/scripts/README.md`、`src/CloverSec-CTF-Build-Dockerizer/docs/validation_guide.md` | 已承接 |

## 新入口保留的硬规则

`SKILL.md` 不再承载完整手册，但必须保留以下会影响行为的内容：

- 首选 `workflow.py`。
- Proposal Gate 触发条件。
- 非低风险输入必须先输出 proposal。
- 用户只能回复 `OK` 或返回修改后的 `CONFIG PROPOSAL` YAML。
- 5 个确认项。
- 未确认前不得 render。
- `--manual` 必须带 reason。
- 平台 `/start.sh`、`/changeflag.sh`、`/bin/bash`、`/flag` 规则。
- Scenario/Bundle/Linux-QEMU/check-service 边界。
- 按需读取索引。

`scripts/doc_guard.py` 会检查这些关键入口，避免后续修改误删。

## 不再逐字放在入口文件里的内容

以下内容仍保留在仓库中，但不再放入 `SKILL.md`：

- 字段大表：`src/CloverSec-CTF-Build-Dockerizer/data/schema.md`。
- 逐栈长说明：`src/CloverSec-CTF-Build-Dockerizer/docs/stack_cookbook.md`。
- 长 YAML 模板：`src/CloverSec-CTF-Build-Dockerizer/docs/orchestrated_workflow.md`。
- 常见错误表：`src/CloverSec-CTF-Build-Dockerizer/docs/validation_guide.md`。
- 发布命令附录：`src/CloverSec-CTF-Build-Dockerizer/scripts/README.md`。
- 排障剧本：`src/CloverSec-CTF-Build-Dockerizer/docs/troubleshooting.md`。

原因：这些内容对每次 Skill 触发并非都需要，放入口文件会增加上下文负担。需要时按 `SKILL.md` 的索引读取对应文档。
