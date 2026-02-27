# data 目录

- `stacks.yaml`：9 个技术栈（node/php/python/java/tomcat/lamp/pwn/ai/rdg）的识别特征与默认参数。
- `patterns.yaml`：端口/启动命令/入口文件推断规则（用于缺省字段自动补全，支持轻量内容匹配信号）。
- `schema.md`：`challenge.yaml` 稳定输入 schema（v1）定义与约束说明。
- `validate_rules.yaml`：`validate.sh` 可配置规则（可增量扩展而不改脚本）。

说明：

- 平台硬约束（`/start.sh`、`/flag`、`/bin/bash`）仍由脚本硬规则强制校验；仅 RDG 且 `include_flag_artifact=false` 时可放行 `/flag`。
- `v1.4.0` 起新增 `challenge.healthcheck` 与 `challenge.platform.allow_loopback_bind` 配置模型，并在 `render.py/validate.sh` 中真实生效。
