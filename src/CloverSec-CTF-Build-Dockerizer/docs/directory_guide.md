# 目录指引（v2.2.0）

## Skill 根目录

已安装 Skill 的根目录包含：

- `SKILL.md`：技能协议
- `data/`：schema / stacks / profiles / components / scenario / rules
- `templates/`：12 栈模板与 snippets，含 `linux-qemu`
- `scripts/`：derive / parse / render / validate / Linux-QEMU 手动检查
- `examples/`：单题 + baseunit + secops + linux-qemu + scenario 示例
- `docs/`：架构 / 契约 / 手册

## 脚本职责边界

`scripts/` 用于题目构建链路：

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
