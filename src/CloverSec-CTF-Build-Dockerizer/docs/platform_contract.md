# 平台契约（Platform Contract, v2.0.1）

本文档定义交付到目标平台时必须满足的运行契约。

## 1. 固定启动入口

平台固定按以下方式拉起容器：

```bash
docker run -d -p <host>:<container> <image>:latest /start.sh
```

因此必须满足：

- `/start.sh` 存在
- `/start.sh` 可执行
- `/start.sh` 启动真实服务并保持容器有效运行

## 2. 动态 flag 写入入口

平台会调用：

```bash
/bin/bash /changeflag.sh
```

因此必须满足：

- 镜像内存在 `/bin/bash`
- 镜像内存在 `/changeflag.sh`
- `/changeflag.sh` 可执行

## 3. `/flag` 产物规则

默认要求：

- 交付目录包含 `flag`
- Dockerfile 把 `flag` 复制到 `/flag`
- `/flag` 具备可读权限（通常 `444`）

可选放行：

- 当 defense 语义中 `include_flag_artifact=false` 时，可放行 `/flag`
- 该放行不影响 `/changeflag.sh`（仍是硬约束）

## 4. 进程与保活规则

必须：

- 单服务模式使用 `exec` 作为 PID1
- 多服务模式至少有真实前台主进程

禁止：

- `sleep infinity`
- `while true; do sleep ...; done`
- 仅 `tail -f /dev/null` 的空转保活

## 5. 网络与端口规则

- Dockerfile 必须声明 `EXPOSE`
- 默认要求对外可达监听；如题型确需回环监听，需显式设置 `platform.allow_loopback_bind=true`

## 6. V2 profile/defense 语义

- 主配置：`challenge.profile` + `challenge.defense`
- 兼容输入：`challenge.rdg`
- profile 覆盖：`jeopardy / rdg / awd / awdp / secops`

## 7. Scenario 边界

Scenario 模式可生成 `docker-compose.yml` 用于本地多服务验证，但平台最终交付仍是单服务目录：

- `Dockerfile`
- `start.sh`
- `changeflag.sh`

## 8. AWDP 补丁契约

最终 profile 为 `awdp` 的服务，必须存在：

- `patch/src/`
- 可执行 `patch/patch.sh`
- `patch_bundle.tar.gz`（且包含上面两项）

## 9. 最小交付清单

每次渲染完成后，至少应看到：

- `Dockerfile`
- `start.sh`
- `changeflag.sh`
- `challenge.yaml`
- `flag`（可按 `include_flag_artifact=false` 放行）

## 10. 关联文档

- 输入 Schema：`src/CloverSec-CTF-Build-Dockerizer/data/schema.md`
- 栈手册：`src/CloverSec-CTF-Build-Dockerizer/docs/stack_cookbook.md`
- 场景 Schema：`src/CloverSec-CTF-Build-Dockerizer/data/scenario_schema.md`
- 校验规则：`src/CloverSec-CTF-Build-Dockerizer/data/validate_rules.yaml`
