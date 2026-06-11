# 平台契约（Platform Contract, v2.2.0）

本文档定义交付到目标平台时必须满足的运行契约。文档描述以当前仓库实现为准，不额外扩展未落地能力。

## 目录

- 1. 固定启动入口
- 2. 动态 flag 写入入口
- 3. `/flag` 产物规则
- 4. 进程与保活规则
- 5. 网络与端口规则
- 6. V2 profile / defense 语义
- 7. Linux-QEMU 边界
- 8. Scenario 边界
- 9. AWDP 补丁契约
- 10. 最小交付清单
- 11. 关联文档

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

业务同步：

- 平台只保证动态 flag 写入 `/flag`。
- 如果题目程序读取其他路径，例如 `/home/ctf/flag0`、`/home/ctf/flag1` 或 `/challenge/flag.php`，应配置 `challenge.flag.sync_paths`。
- `changeflag.sh` 会把动态 flag 同步到这些路径；`validate.sh` 只做隔离动态写入检查，不会在宿主机写这些绝对路径。
- `sync_paths` 不是启动时初始化机制。平台或本地验证必须调用 `/changeflag.sh` 后，业务路径才保证拿到动态 flag；`start.sh` 只保留模板内明确写出的兼容路径。

可选放行：

- 当当前 profile 使用 defense 语义，且显式设置 `include_flag_artifact=false` 时，可放行 `/flag`
- 该放行不影响 `/changeflag.sh`（仍是硬约束）
- 当前代码中的放行语义以实际 profile/stack 支持范围为准，文档不额外放大

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

## 6. V2 profile / defense 语义

- 主配置：`challenge.profile` + `challenge.defense`
- 兼容输入：`challenge.rdg`
- profile 覆盖：`jeopardy / rdg / awd / awdp / secops`

## 7. Linux-QEMU 边界

`stack=linux-qemu` 仍交付单 Docker 镜像，平台入口不变：

- 平台只看到外层容器 `/start.sh`
- `/start.sh` 在容器内启动 QEMU
- vulnerable kernel、initrd/rootfs 位于 QEMU guest 内
- Docker 宿主机内核不会被替换

运行约束：

- 默认使用 TCG，不要求平台提供 `/dev/kvm`
- 使用 KVM 时必须由题目配置显式声明，并由运行平台显式提供 `/dev/kvm`
- 不默认要求 `--privileged`
- QEMU monitor、gdbstub、TCP console 不得默认对外开放
- Docker `EXPOSE` 与 QEMU `hostfwd` 必须一致

flag 约束：

- 外层 `/flag` 仍是平台契约入口
- guest 内读取 flag 时，`/changeflag.sh` 必须同步写入 guest rootfs，或在配置中显式关闭 guest flag 注入

## 8. Scenario 边界

Scenario 模式可生成 `docker-compose.yml` 用于本地多服务验证，但平台最终交付仍是单服务目录，核心交付件是：

- `Dockerfile`
- `start.sh`
- `changeflag.sh`

## 9. AWDP 补丁契约

最终 profile 为 `awdp` 的服务，必须存在：

- `patch/src/`
- 可执行 `patch/patch.sh`
- `patch_bundle.tar.gz`（且包含上面两项）

## 10. 最小交付清单

每次渲染完成后，至少应看到：

- `Dockerfile`
- `start.sh`
- `changeflag.sh`
- `flag`（可按 `include_flag_artifact=false` 放行）

`challenge.yaml` 是输入配置文件，常驻于工作目录或示例目录中，但不是 `render.py` 对所有路径都统一保证重新输出的硬产物。

## 11. 关联文档

- 输入 Schema：`data/schema.md`
- 栈手册：`docs/stack_cookbook.md`
- 场景 Schema：`data/scenario_schema.md`
- 校验规则：`data/validate_rules.yaml`
- 校验规则：`docs/validation_guide.md`
