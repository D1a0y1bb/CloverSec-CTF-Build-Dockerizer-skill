# 目录指引（v2.2.0）

## Skill 根目录

已安装 Skill 的根目录包含：

- `SKILL.md`：默认任务、输出合同和高级模式路由
- `data/`：schema / stacks / profiles / components / scenario / rules
- `templates/`：12 栈模板与 snippets，含 `linux-qemu`
- `scripts/`：`ctfctl.py` 默认入口，以及 derive / parse / render / validate / Linux-QEMU 手动检查
- `examples/`：单题 + baseunit + secops + linux-qemu + scenario 示例
- `docs/`：架构 / 契约 / 手册

## 脚本职责边界

`scripts/` 用于题目构建链路。普通题目先使用 `ctfctl.py`，高级输入再进入底层脚本：

- `ctfctl.py`
- `derive_config.py`
- `parse_config_block.py`
- `render.py`
- `render_bundle.py`
- `render_component.py`
- `render_scenario.py`
- `validate.sh`
- `validate_bundle.py`
- `validate_scenario.py`
- `linux_qemu_manual_check.sh`
- `verify_asset_manifest.py`
