# 架构总览（v1.5.0）

本文档用于说明 CloverSec-CTF-Build-Dockerizer 的分层设计与数据流，便于维护者快速定位问题与扩展点。

## 1) 输入层（Input Contract）

- `data/schema.md`：定义 `challenge.yaml` 的稳定输入契约。
- `data/stacks.yaml`：定义 9 栈默认参数与 detect 特征。
- `data/runtime_profiles.yaml`：定义 `php/node/java` 运行时档位与基础镜像映射。
- `data/patterns.yaml`：定义启动命令、端口、入口文件等推断规则。

## 2) 推断层（Inference）

- `src/CloverSec-CTF-Build-Dockerizer/scripts/detect_stack.py`：栈侦测入口。
- `src/CloverSec-CTF-Build-Dockerizer/scripts/derive_config.py`：输出 `CONFIG PROPOSAL` 所需的完整提案（含门禁提示与运行时档位候选）。
- `src/CloverSec-CTF-Build-Dockerizer/scripts/utils.py`：推断、公用模板处理、runtime profile 映射等通用逻辑。

## 3) 渲染层（Render）

- `src/CloverSec-CTF-Build-Dockerizer/scripts/parse_config_block.py`：把 CONFIG PROPOSAL 规范化为 `challenge.yaml`。
- `src/CloverSec-CTF-Build-Dockerizer/scripts/render.py`：按配置渲染 `Dockerfile/start.sh/flag(可选)/check`。
- `src/CloverSec-CTF-Build-Dockerizer/templates/<stack>/`：栈特有模板。
- `src/CloverSec-CTF-Build-Dockerizer/templates/snippets/`：横切能力片段（prolog/epilog/bash/bootstrap/healthcheck 等）。

## 4) 校验层（Validate）

- `src/CloverSec-CTF-Build-Dockerizer/scripts/validate.sh`：平台硬约束 + 规则校验 + 风险提示。
- `src/CloverSec-CTF-Build-Dockerizer/scripts/autofix.py`：安全小修复（dry-run / write）。
- `src/CloverSec-CTF-Build-Dockerizer/scripts/validate_examples.sh`：样例批量静态回归。
- `src/CloverSec-CTF-Build-Dockerizer/scripts/smoke_test.sh`：构建运行级回归。

## 5) 发布治理层（Release Governance）

- 根目录 `scripts/` 为治理入口，v1.5.0 起采用 Python 主实现 + Shell 兼容入口：
- `scripts/doc_guard.py` + `scripts/doc_guard.sh`
- `scripts/release_build.py` + `scripts/release_build.sh`
- `scripts/generate_sbom.py` + `scripts/generate_sbom.sh`
- `scripts/sync.py` + `scripts/sync.sh`
- `scripts/publish_guard.py`（供 `scripts/publish_release.sh` 调用）
- `scripts/publish_release.sh`（发布编排器）

## 6) 关键约束

- 平台固定以 `/start.sh` 启动容器。
- 默认要求 `/flag` 与 `/bin/bash`；RDG 且 `include_flag_artifact=false` 可放行 `/flag`。
- `Dockerfile` 必须声明 `EXPOSE`。
- 禁止空转保活（如 `sleep infinity`）。

## 7) 典型数据流

1. `derive_config.py` 从源码目录提取栈、端口、启动候选、运行时档位建议。  
2. 用户确认（OK 或回传 YAML）后，`parse_config_block.py` 生成 `challenge.yaml`。  
3. `render.py` 产出交付文件。  
4. `validate.sh` 与回归脚本执行质量门禁。  
5. `release_build.py` 生成 zip + SBOM；`publish_release.sh` 完成 tag/release/上传。  
