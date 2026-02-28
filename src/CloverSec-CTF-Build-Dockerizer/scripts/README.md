# scripts 目录说明

职责边界：

- 仓库根目录 `scripts/` 负责发布治理与仓库级流程（如 `release_build.sh`、`publish_release.sh`、`doc_guard.sh`）。
- 本目录 `src/CloverSec-CTF-Build-Dockerizer/scripts/` 负责引擎运行链路（探测、渲染、校验、回归）。

## 脚本列表

- `render.py`：根据 challenge.yaml 或 CLI 参数渲染 Dockerfile/start.sh/flag
- `derive_config.py`：自动探测并输出 ProposedConfig（AI 编排模式专用）
- `parse_config_block.py`：解析 CONFIG PROPOSAL YAML（stdin）并生成标准 challenge.yaml
- `detect_stack.py`：输出技术栈侦测结果和置信度
- `validate.sh`：执行硬规则与可配置规则校验
- `autofix.py`：`validate.sh --fix/--fix-write` 对应的安全自动修复执行器
- `validate_examples.sh`：遍历 examples 全目录并做静态校验
- `smoke_test.sh`：执行 render/validate/build/run 冒烟回归
- `test_runtime_profiles.sh`：运行时档位推断回归（php/node/java）
- `cleanup_test_containers.sh`：清理 `ctf-skill-test*` 容器和镜像
- `utils.py`：模板 include、变量渲染、推断与通用函数

## 常用命令

```bash
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/derive_config.py --project-dir .
```

```bash
cat config-proposal.yaml | python3 src/CloverSec-CTF-Build-Dockerizer/scripts/parse_config_block.py --output challenge.yaml
```

```bash
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/render.py --config path/to/challenge.yaml
bash src/CloverSec-CTF-Build-Dockerizer/scripts/validate.sh Dockerfile start.sh challenge.yaml
bash src/CloverSec-CTF-Build-Dockerizer/scripts/validate_examples.sh
bash src/CloverSec-CTF-Build-Dockerizer/scripts/smoke_test.sh
```
