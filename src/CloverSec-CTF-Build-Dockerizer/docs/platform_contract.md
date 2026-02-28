# 平台契约（Platform Contract）

本文档解释 CloverSec-CTF-Build-Dockerizer 必须遵守的平台运行契约，以及这些约束背后的工程原因。

## 1. 固定启动方式

平台固定使用以下方式启动镜像：

```bash
docker run -d -p <host_port>:<container_port> <image>:latest /start.sh
```

约束含义：

- 镜像里必须存在 `/start.sh`。
- `/start.sh` 必须可执行。
- `/start.sh` 需要完成服务启动，并让容器持续运行。
- `/start.sh` 需要输出可观测日志，便于运维和出题人排障。

## 2. 为什么必须使用 /start.sh

平台不会依赖镜像默认 `ENTRYPOINT` 或 `CMD`，而是直接附加 `/start.sh` 参数。

工程后果：

- 即使 Dockerfile 中已有 `CMD`，仍必须保证 `/start.sh` 独立可执行。
- start.sh 必须是完整的启动入口，不能只做环境准备然后退出。

## 3. 为什么默认要求 /flag 在容器根目录

平台会在容器启动后注入动态 flag。技能交付时需要提供固定路径的静态测试 flag 文件：

- 路径：`/flag`
- 权限：可读（建议 `444`）

工程后果（默认模式）：

- Dockerfile 需要把 `flag` 拷贝到 `/flag`。
- Dockerfile 需要设置 `/flag` 读权限。

RDG 例外（显式配置）：

- 当 `challenge.rdg.include_flag_artifact=false` 时，可关闭 `/flag` 产物链路，用于 check-service 判定题型。

## 4. 为什么必须安装 bash

平台动态 flag 写入机制调用：

```bash
/bin/bash /changeflag.sh
```

工程后果：

- 镜像内必须存在 `/bin/bash`。
- 不能只依赖 `/bin/sh`。
- 基础镜像若默认不带 bash，必须显式安装 bash。

## 5. 为什么单服务必须 exec 主进程

单服务场景推荐模式：

```bash
exec <main_process>
```

原因：

- 主进程作为 PID1 时能正确接收并处理终止信号。
- 避免脚本退出后容器直接退出。
- 避免“服务在后台运行但容器前台空转”的假活状态。

## 6. 为什么禁止空转保活

禁止以下模式：

- `sleep infinity`
- `while true; do sleep ...; done`

原因：

- 这类逻辑不代表业务服务可用，只是让容器看起来在运行。
- 平台检查与排障会被误导。

## 7. 多服务场景的可接受策略

LAMP 等多服务场景允许：

- 后台启动一个服务 + 前台 `exec` 另一个服务。
- tail 真实日志文件（例如 Apache 日志）。

不推荐：

- `tail -f /dev/null` 作为唯一前台逻辑。

建议：

- 若进程管理复杂，可引入轻量 supervisor。

## 8. 镜像瘦身与可维护性要求

必须遵守：

- Alpine: `apk add --no-cache ...`
- Debian/Ubuntu: `apt-get ... && rm -rf /var/lib/apt/lists/*`
- Python: `pip install --no-cache-dir ...`
- Node: 优先 `npm ci`，并清理 npm cache

原因：

- 降低镜像体积，加快分发和加载速度。
- 减少无效缓存带来的安全与维护负担。

## 9. 输出契约

每次渲染交付默认必须有：

- `Dockerfile`
- `start.sh`
- `flag`（RDG 且 `include_flag_artifact=false` 可关闭）

并满足：

- Dockerfile 有中文注释，说明关键步骤原因。
- start.sh 有中文注释，说明启动策略和平台约束。
- `validate.sh` 校验通过（至少无 ERROR）。

## 10. 与其它文档的关系

- 栈与默认值：`src/CloverSec-CTF-Build-Dockerizer/data/stacks.yaml`
- 输入契约：`src/CloverSec-CTF-Build-Dockerizer/data/schema.md`
- 可配置校验规则：`src/CloverSec-CTF-Build-Dockerizer/data/validate_rules.yaml`
- 故障定位与修复：`src/CloverSec-CTF-Build-Dockerizer/docs/troubleshooting.md`
