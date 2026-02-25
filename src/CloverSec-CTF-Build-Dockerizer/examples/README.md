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
  - `ai-basic/`
  - `ai-transformers-basic/`
  - `rdg-php-hardening-basic/`
  - `rdg-python-ssti-basic/`
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
