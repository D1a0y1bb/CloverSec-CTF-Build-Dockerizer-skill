# data 目录（v2.0.0）

- `schema.md`：`challenge.yaml` v2 输入契约
- `stacks.yaml`：11 栈默认值与探测规则
- `patterns.yaml`：端口/启动命令推断规则
- `profiles.yaml`：profile 默认防御行为
- `runtime_profiles.yaml`：php/node/java 运行时档位映射
- `components.yaml`：baseunit 组件与版本变体
- `scenario_schema.md`：scenario 输入约定
- `validate_rules.yaml`：单题规则校验
- `validate_scenario_rules.yaml`：scenario 校验规则
- `base_image_allowlist.yaml`：发布门禁白名单

说明：

- 平台硬约束由渲染与校验链路强制执行（`/start.sh`、`/changeflag.sh`、`/bin/bash`、`EXPOSE`）。
- `/flag` 默认必须存在，仅在 `include_flag_artifact=false` 时可放行。
- scenario 生成的 compose 为本地验证用途，不改变平台单服务交付模型。
