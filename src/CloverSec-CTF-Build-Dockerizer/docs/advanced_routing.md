# Advanced routing

普通单服务题目不需要读取本文。

## 触发条件

| 事实或请求 | 使用入口 | 继续读取 |
|---|---|---|
| 历史题目包含完整 Dockerfile 和旧 helper | `ctfctl.py --profile preserve` | `docs/legacy_migration.md` |
| 用户明确要求旧平台 helper | `render.py` | `docs/platform_contract_legacy_v2.md` |
| 输入包含 compose 或 Vulhub-like | `import_compose.py` | `data/scenario_schema.md` |
| 用户需要多个服务本地联调 | `render_scenario.py` | `data/scenario_schema.md`、`docs/validation_guide.md` |
| 用户需要 Bundle 或 BaseUnit | `render_bundle.py`、`render_component.py` | `docs/bundle_design.md` |
| 输入属于 RDG、AWD、AWDP 或 SecOps | `generate_check_stub.py`、`validate.sh` | `docs/validation_guide.md` |
| 题目需要指定 Linux 内核或 guest rootfs | `render.py`、`linux_qemu_manual_check.sh` | `docs/linux_qemu_manual_validation.md` |
| 用户要导出 amd64 镜像、image tar 或表格字段 | `docker_artifacts.py` | `scripts/README.md` 中的 Docker artifact 章节 |

`ctfctl.py inspect` 会把 compose、Scenario 和 Bundle 文件列入 `advanced_inputs`，并在 `advanced_route` 中给出后续入口。看到这些字段时，不要把它们静默当作普通单服务输入。先保留原始目录，再选择对应入口或使用 `preserve`。

`ctfctl.py scaffold --profile clean` 在 attachment-only 输入中保留 `challenge.yaml` 和高级资料。`ctfctl.py package` 会归档这些资料，但返回 `partial`，直到高级入口生成可构建服务目录。

## 高级模式边界

- 高级模式不会改变普通题目的 direct-exec 默认合同。
- Scenario 的 compose 只用于本地编排和验证。
- Bundle custom 组合必须由用户提供安装命令、启动命令、端口和服务清单。
- Linux-QEMU 的 guest Flag 写入必须使用 guest 专用合同。
- check-service 生成器只生成待审查骨架，不把 `CHECK_REVIEW_REQUIRED` 当成通过。
- Release、SBOM 和 GitHub 发布脚本属于仓库维护流程，不属于题目构建默认流程。
- `clean` 只移除未被 Dockerfile、start.sh 或 challenge.yaml 引用的明确作者辅助文件。它不会删除高级模式需要的运行资产。

## 结果

高级模式仍然输出最小服务目录。

机器报告写入 `.ctfbuild/` 或高级模式自己的报告目录。

不要把 Scenario、Bundle、QEMU 和 Release 的全部说明复制回 `SKILL.md`。
