# examples 目录说明

本目录同时保留两类示例：

- 标准回归目录（建议优先使用）：
  - `node-basic/`
  - `php-apache-basic/`
  - `python-flask-basic/`
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
  - `bundle-legacy-centos7-webstack/`（Bundle/Recipe 输入示例）
  - `bundle-tomcat8-mysql57/`（Bundle/Recipe 输入示例）
  - `scenario-compose-import-basic/`（compose 导入草案示例）
- 兼容目录（保留历史路径）：
  - `node/`
  - `php/`
  - `python/`
  - `java/`
  - `tomcat/`
  - `lamp/`

每个目录都包含：

- `challenge.yaml`：渲染输入
- 最小应用文件（源码或二进制制品）
- `README.md`：本目录的快速运行说明
- 可选渲染产物：`Dockerfile`、`start.sh`、`flag`
- RDG 示例额外包含：`check/check.sh`（check-service 真实检查脚本）
- 可选冒烟断言：`smoke_assert.sh`（由 `smoke_test.sh` 自动调用）
- 当前 Web/Java/Tomcat 关键示例的 `smoke_assert.sh` 会校验 HTTP 响应内容，不只判断容器是否运行。
- `linux-qemu-basic/` 默认只用于渲染与静态校验；完整 QEMU boot 需要替换真实 VM 资产后单独执行。
- `bundle-*` 默认只保存 `bundle.yaml` 输入和最小应用文件；批量回归会在临时目录渲染后校验。
- `scenario-compose-import-basic/` 默认生成 `scenario.draft.yaml`、`scenario.renderable.yaml` 与 `import-report.json` 后再校验可渲染子集。

批量回归入口：

```bash
bash scripts/validate_examples.sh
bash scripts/smoke_test.sh
```

`validate_examples.sh` 默认只读执行，会把示例复制到临时目录再渲染和校验，不写回本目录。
