# data 目录（v2.2.0）

- `schema.md`：`challenge.yaml` v2 输入契约
- `stacks.yaml`：12 栈默认值与探测规则（含 `linux-qemu`）
- `patterns.yaml`：端口/启动命令推断规则
- `profiles.yaml`：profile 默认防御行为
- `runtime_profiles.yaml`：php/node/java 运行时档位映射
- `components.yaml`：baseunit 组件与版本变体
- `bundle_schema.md`：Bundle/Recipe 输入契约
- `bundle_recipes.yaml`：Bundle/Recipe 固定组合定义
- `scenario_schema.md`：scenario 输入约定
- `validate_rules.yaml`：单题规则校验
- `validate_scenario_rules.yaml`：scenario 校验规则
- `base_image_allowlist.yaml`：交付校验白名单

说明：

- 平台硬约束由渲染与校验链路强制执行（`/start.sh`、`/changeflag.sh`、`/bin/bash`、`EXPOSE`）。
- `/flag` 默认必须存在，仅在受支持的 defense profile 显式设置 `include_flag_artifact=false` 时可放行。
- scenario 生成的 compose 为本地验证用途，不改变平台单服务交付模型。
- bundle 覆盖固定 Recipe 和显式 custom 组合；custom 组合必须提供安装命令、启动命令、端口和服务清单，不做自动版本求解。
- `linux-qemu` 使用 `challenge.vm` 描述 QEMU guest、VM 资产、hostfwd 和 guest flag 注入策略。
