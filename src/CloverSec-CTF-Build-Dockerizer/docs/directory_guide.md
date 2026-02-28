# 目录指引（v1.5.0）

本文档专门说明仓库目录职责，避免“同名脚本不知道该改哪份”的维护风险。

## 仓库根目录

- `README.md` / `README.zh-CN.md`：对外主文档。
- `CHANGELOG.md`：版本变更记录。
- `VERSION`：当前发布版本号。
- `scripts/`：仓库治理与发布编排入口（Python 主实现 + `.sh` 兼容入口）。
- `src/CloverSec-CTF-Build-Dockerizer/`：技能真源目录（发布包核心内容）。
- `Build_test/`：真实业务样例（展示生成结果与复现链路）。
- `dist/`：发布产物目录（zip/sbom/deps）。

## `src/CloverSec-CTF-Build-Dockerizer/`

- `SKILL.md`：技能协议与 AI 编排规范。
- `data/`：规则与配置模型。
- `templates/`：9 栈模板 + snippets 片段。
- `scripts/`：引擎运行链路（derive/render/validate/smoke）。
- `examples/`：回归样例集合。
- `docs/`：开发/使用/排障文档。

## 脚本职责边界（重点）

### 根目录 `scripts/`

用于发布治理与仓库级质量控制：

- `doc_guard.py(.sh)`：文档一致性守卫。
- `release_build.py(.sh)`：发布打包与发布前检查。
- `generate_sbom.py(.sh)`：SBOM 与依赖清单生成。
- `sync.py(.sh)`：技能同步到 Claude/Codex/Trae 目录。
- `publish_guard.py`：发布白名单与版本守卫。
- `publish_release.sh`：发布编排（commit/tag/release/upload）。

### 引擎目录 `src/CloverSec-CTF-Build-Dockerizer/scripts/`

用于题目容器化主链：

- `derive_config.py`
- `parse_config_block.py`
- `render.py`
- `validate.sh`
- `autofix.py`
- `validate_examples.sh`
- `smoke_test.sh`

## 修改建议

- 规则或默认值问题：优先改 `data/`。  
- 生成结果问题：优先改 `templates/` 与 `render.py`。  
- 误报/漏报问题：优先改 `validate.sh` 与 `data/validate_rules.yaml`。  
- 发布链路问题：优先改根目录 `scripts/`。  
