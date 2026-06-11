# examples 目录说明

本目录按输入类型保留示例。不同输入类型对应不同入口脚本，不要把所有目录都当成普通 `challenge.yaml` 单题示例。

## `challenge.yaml` 单题示例

这些目录以 `challenge.yaml` 为主输入，使用 `render.py` / `validate.sh`：

  - `node-basic/`
  - `php-apache-basic/`
  - `python-flask-basic/`（包含 `challenge.verification.solve_probe` 官方示例）
  - `java-jar-basic/`
  - `tomcat-war-basic/`
  - `lamp-basic/`
  - `pwn-basic/`
  - `pwn-alpine-tcpserver-basic/`
  - `ai-basic/`
  - `ai-transformers-basic/`
  - `rdg-php-hardening-basic/`
  - `rdg-python-ssti-basic/`
  - `lamp-alpine-basic/`
  - `python-loopback-ssrf-basic/`
  - `node-multiport-basic/`
  - `python-supervisor-basic/`
  - `pwn-socat-basic/`
  - `tomcat-context-basic/`
  - `linux-qemu-basic/`（轻量 render/validate 示例，占位 VM 资产不可 boot）

## `bundle.yaml` Bundle/Recipe 示例

这些目录以 `bundle.yaml` 为主输入，使用 `render_bundle.py` / `validate_bundle.py`：

  - `bundle-legacy-centos7-webstack/`
  - `bundle-tomcat8-mysql57/`
  - `bundle-custom-explicit/`

## `scenario.yaml` Scenario 示例

这些目录以 `scenario.yaml` 为主输入，使用 `render_scenario.py --accepted --reason ...` / `validate_scenario.py --validate-rendered`：

  - `scenario-awd-basic/`
  - `scenario-awdp-basic/`
  - `scenario-vulhub-like-basic/`

## Compose import 示例

这些目录以 `docker-compose.yml` 为主输入，使用 `import_compose.py`，只把 `scenario.renderable.yaml` 继续交给 `render_scenario.py`：

  - `scenario-compose-import-basic/`

## 兼容目录

保留历史路径，仍按 `challenge.yaml` 单题示例处理：

  - `node/`
  - `php/`
  - `python/`
  - `java/`
  - `tomcat/`
  - `lamp/`

`challenge.yaml` 单题示例通常包含：

- `challenge.yaml`：渲染输入
- 最小应用文件（源码或二进制制品）
- `README.md`：本目录的快速运行说明
- 可选渲染产物：`Dockerfile`、`start.sh`、`flag`
- 可选业务入口断言：`challenge.verification.solve_probe` 或 `smoke_assert.yaml`
- RDG 示例额外包含：`check/check.sh`（check-service 真实检查脚本）
- `linux-qemu-basic/` 默认只用于渲染与静态校验；完整 QEMU boot 需要替换真实 VM 资产后单独执行。
- `bundle-*` 默认只保存 `bundle.yaml` 输入和最小应用文件。
- `scenario-compose-import-basic/` 默认生成 `scenario.draft.yaml`、`scenario.renderable.yaml` 与 `import-report.json` 后再校验可渲染子集。
