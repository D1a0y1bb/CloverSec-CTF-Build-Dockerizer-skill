# 目录指引（v2.0.1）

## 仓库根目录

- `README.md` / `README.zh-CN.md` / `README.ja.md` / `README.en.md`
- `CHANGELOG.md`
- `VERSION`
- `scripts/`（发布治理）
- `src/CloverSec-CTF-Build-Dockerizer/`（技能主目录）
- `dist/`（发布资产）

## 技能主目录

`src/CloverSec-CTF-Build-Dockerizer/`：

- `SKILL.md`：技能协议
- `data/`：schema/stacks/profiles/components/scenario/rules
- `templates/`：11 栈模板与 snippets
- `scripts/`：derive/parse/render/validate/smoke
- `examples/`：单题 + baseunit + secops + scenario 示例
- `docs/`：架构/契约/手册

## 脚本职责边界

### 根目录 `scripts/`

用于发布治理：

- `doc_guard.sh`
- `release_build.sh`
- `publish_release.sh`

### 技能目录 `src/CloverSec-CTF-Build-Dockerizer/scripts/`

用于题目构建链路：

- `derive_config.py`
- `parse_config_block.py`
- `render.py`
- `render_component.py`
- `render_scenario.py`
- `validate.sh`
- `validate_scenario.py`
- `validate_examples.sh`
- `smoke_test.sh`

## 建议修改路径

- 输入与默认值问题：改 `data/`
- 渲染产物问题：改 `templates/` + `render.py`
- 场景编排问题：改 `render_scenario.py` + `validate_scenario.py`
- 校验误报/漏报：改 `validate.sh` + `data/validate_rules.yaml`
- 发布问题：改根目录 `scripts/`
