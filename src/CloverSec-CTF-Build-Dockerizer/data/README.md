# data 目录

- `stacks.yaml`：9 个技术栈（node/php/python/java/tomcat/lamp/pwn/ai/rdg）的识别特征与默认参数。
- `patterns.yaml`：端口/启动命令/入口文件推断规则（用于缺省字段自动补全，支持轻量内容匹配信号）。
- `schema.md`：`challenge.yaml` 稳定输入 schema（v1）定义与约束说明。
- `validate_rules.yaml`：`validate.sh` 可配置规则（可增量扩展而不改脚本）。
- `base_image_allowlist.yaml`：发布级 digest 门禁下允许 tag-only 放行的官方基础镜像白名单。
- `runtime_profiles.yaml`：`php/node/java` 运行时档位映射（用于 AI 五问与 `--runtime-profile`）。

说明：

- 平台硬约束（`/start.sh`、`/flag`、`/bin/bash`）仍由脚本硬规则强制校验；仅 RDG 且 `include_flag_artifact=false` 时可放行 `/flag`。
- `v1.4.0` 起新增 `challenge.healthcheck` 与 `challenge.platform.allow_loopback_bind` 配置模型，并在 `render.py/validate.sh` 中真实生效。
- `v1.4.0-r1` 起发布流程支持 digest 门禁：`VALIDATE_ENFORCE_DIGEST=1` 时，非 digest 且非白名单镜像将触发 ERROR。
- `v1.5.0` 起新增运行时档位能力：`derive_config.py` 输出 `runtime_profile_candidates`，`render.py` 支持 `--runtime-profile`，并保持 `base_image` 作为最终生效值。
