# 架构总览（v2.0.3）

## 1) 输入层

- `data/schema.md`：`challenge.yaml` v2 输入契约
- `data/stacks.yaml`：11 栈默认值与探测特征
- `data/profiles.yaml`：profile 默认防御配置
- `data/runtime_profiles.yaml`：php/node/java 运行时档位映射
- `data/components.yaml`：baseunit 组件与变体定义
- `data/scenario_schema.md`：scenario 输入约定

## 2) 推断与提案层

- `src/CloverSec-CTF-Build-Dockerizer/scripts/derive_config.py`：自动推断 + `config_proposal` 输出
- `src/CloverSec-CTF-Build-Dockerizer/scripts/parse_config_block.py`：把 `CONFIG PROPOSAL` 转为 `challenge.yaml`
- `src/CloverSec-CTF-Build-Dockerizer/scripts/utils.py`：模板渲染、公用推断、runtime/profile 工具函数

## 3) 渲染层

- `src/CloverSec-CTF-Build-Dockerizer/scripts/render.py`：单题渲染主入口
- `src/CloverSec-CTF-Build-Dockerizer/scripts/render_component.py`：baseunit 组件渲染入口
- `src/CloverSec-CTF-Build-Dockerizer/scripts/render_scenario.py`：场景渲染入口（本地 compose）
- `templates/<stack>/`：栈模板
- `templates/snippets/`：横切片段（changeflag/defense/healthcheck 等）

## 4) 校验层

- `src/CloverSec-CTF-Build-Dockerizer/scripts/validate.sh`：平台硬规则 + 风险规则
- `src/CloverSec-CTF-Build-Dockerizer/scripts/validate_scenario.py`：scenario 规则校验
- `src/CloverSec-CTF-Build-Dockerizer/scripts/validate_examples.sh`：example/scenario 批量回归
- `src/CloverSec-CTF-Build-Dockerizer/scripts/smoke_test.sh`：容器构建与运行冒烟

## 5) 发布治理层

根目录 `scripts/`：

- `doc_guard.py`
- `release_build.py`
- `generate_sbom.py`
- `publish_guard.py`
- `publish_release.sh`

## 6) 核心约束

- 最终交付必须包含：`Dockerfile/start.sh/changeflag.sh`
- `/flag` 仅在受支持的 defense profile 显式设置 `include_flag_artifact=false` 时可放行
- `docker-compose.yml` 仅用于本地场景编排，不作为平台最终交付
