# 校验指南（v2.2.0）

本文档承接 `SKILL.md` 中迁出的校验细节。入口文件只保留门槛，具体规则按需读取本文档。

## 目录

- 1. 校验入口
- 2. 硬规则
- 3. 常见 ERROR
- 4. 常见 WARN
- 5. RDG / SecOps check-service 门禁
- 6. Linux-QEMU 校验边界
- 7. 自动修复
- 8. 模板变量速查

## 1. 校验入口

单题交付目录：

```bash
bash scripts/validate.sh Dockerfile start.sh challenge.yaml
```

写入机器可读摘要：

```bash
bash scripts/validate.sh \
  --json-summary /tmp/validate-summary.json \
  Dockerfile start.sh challenge.yaml
```

只做快速静态契约检查：

```bash
bash scripts/validate.sh --static-only Dockerfile start.sh challenge.yaml
```

退出码约定：

- `0`：通过。
- `1`：输入能解析，但交付契约或校验规则不通过。
- `2`：配置、路径、依赖或运行环境错误。

验证层级：

| 层级 | 入口 | 适用场景 |
|---|---|---|
| 静态契约检查 | `validate.sh --static-only` | 快速判断 Dockerfile/start.sh/challenge.yaml 是否满足平台基本契约 |
| 动态 flag 写入检查 | `validate.sh` 默认启用，或显式 `--with-dynamic-flag` | 检查 `changeflag.sh` 是否能按平台动态 flag 机制写入 |
| 题目入口验证 | 业务断言验证入口 + `smoke_assert.yaml` 或 `challenge.verification.solve_probe` | 容器启动后检查 HTTP/TCP/container_exec 断言，确认题目服务真的可用 |
| 手动增强验证 | `linux_qemu_manual_check.sh`、Docker smoke、PoC 复现 | Linux-QEMU boot、guest flag、真实服务运行和漏洞复现 |

`validate.sh` 的通过结果只代表平台交付契约成立，不代表题目可解。历史题复刻、Pwn flag 路径、业务登录流、漏洞触发路径，需要通过 smoke 业务断言或 PoC 记录补充证明。

执行 `challenge.verification.solve_probe` 的入口是：

```bash
bash scripts/smoke_test.sh --case <example-name>
```

内置示例 `python-flask-basic` 已写好 HTTP probe，可直接执行：

```bash
bash scripts/smoke_test.sh --case python-flask-basic
```

这个命令会构建并启动示例容器，然后读取 `challenge.yaml` 中的 `challenge.verification.solve_probe`。`validate.sh` 不会执行该 probe。

HTTP、TCP、container_exec、Pwn nc 和动态 flag 路径断言片段见 `docs/solve_probe_recipes.md`。

`--json-summary` 会写入 `verification.level`，Agent 应根据该字段判断本次验证覆盖范围。

Scenario：

```bash
python3 scripts/validate_scenario.py \
  --output /tmp/scenario \
  --validate-rendered
```

Bundle：

```bash
python3 scripts/validate_bundle.py --bundle-dir /tmp/bundle
bash scripts/validate.sh /tmp/bundle/Dockerfile /tmp/bundle/start.sh /tmp/bundle/challenge.yaml
```

## 2. 硬规则

- Dockerfile 必须把 `start.sh` 放到 `/start.sh`。
- Dockerfile 必须把 `changeflag.sh` 放到 `/changeflag.sh`。
- 默认必须把 `flag` 放到 `/flag`，并设置可读权限。
- `start.sh` 首行必须是 `#!/bin/bash`。
- 镜像内必须安装或保留 `/bin/bash`。
- 渲染产物不能残留模板变量。
- `EXPOSE` 与 `challenge.expose_ports` 必须一致。
- 单服务必须用 `exec` 作为 PID1。
- 多服务必须至少有真实前台主进程。

`/flag` 可放行的范围以当前 profile/stack 实现为准，公开描述必须同时提到 `include_flag_artifact=false` 的前提。

## 3. 常见 ERROR

| 现象 | 处理 |
|---|---|
| `/start.sh` 未复制到根目录 | Dockerfile 增加 `COPY start.sh /start.sh` |
| `/changeflag.sh` 缺失 | Dockerfile 增加 `COPY changeflag.sh /changeflag.sh` 并赋权 |
| `/flag` 缺失或权限错误 | 增加 `COPY flag /flag` 和 `chmod 444 /flag`，或确认 profile 是否允许放行 |
| Bash 缺失 | Debian/Ubuntu 安装 `bash`；Alpine 使用 `apk add --no-cache bash` |
| 单服务未使用 `exec` | 将最终启动命令改为 `exec <server command>` |
| 端口不一致 | 同步 Dockerfile `EXPOSE`、`challenge.expose_ports` 和服务监听端口 |
| 模板变量残留 | 检查模板变量名、include 文件和 `challenge.yaml` 字段 |
| AWDP patch 缺失 | 提供 `patch/src/`、可执行 `patch/patch.sh`、`patch_bundle.tar.gz` |

## 4. 常见 WARN

| WARN | 判断 |
|---|---|
| 基础镜像未 pin digest | 正式交付前建议固定 digest；开发示例可接受 |
| localhost/127.0.0.1 监听 | 默认风险较高，SSRF/内部链路题需显式 `platform.allow_loopback_bind=true` |
| 后台启动符 `&` | 多服务常见，但必须有真实前台主进程 |
| 命中 legacy runtime | 常用于老题兼容，交付前确认原因 |

WARN 不等于失败，但最终汇报必须说明影响。

## 5. RDG / SecOps check-service 门禁

推荐调用方式：

```bash
bash check/check.sh [target_ip] [target_port]
```

返回码：

- `0`：检查通过
- `1`：检查失败
- `2`：使用或运行错误

`render.py` 自动生成的 check 脚本是 fail-closed，占位标记必须人工替换。`validate.sh` 会阻断以下情况：

- `CHECK_IMPLEMENT_ME`
- `CHECK_REVIEW_REQUIRED`
- `TODO implement`
- `TODO:`
- `placeholder`
- 脚本过短且直接 `exit 0`

可用骨架生成器减少重复工作：

```bash
python3 scripts/generate_check_stub.py \
  --type http \
  --output check/check.sh \
  --target-port 80 \
  --path / \
  --expect-status 200 \
  --expect-text "login"
```

可选业务断言：

- HTTP：`--expect-status`、`--expect-text`、`--forbid-text`、`--expect-header`、`--forbid-header`。
- Redis：`--redis-key`、`--redis-expect-value`。
- MySQL：`--mysql-query`、`--mysql-expect-text`。
- SSH：`--ssh-expect-banner`。

生成脚本默认带 `CHECK_REVIEW_REQUIRED`。只有人工确认健康检查和漏洞负向检查后，才能移除该标记。

## 6. Linux-QEMU 校验边界

快速校验只做静态检查：

- `challenge.vm` 字段结构
- `vm/vmlinuz`、`vm/initrd.img`、`vm/rootfs.ext4` 或 `build_script` 是否存在
- Docker `EXPOSE` 与 QEMU `hostfwd` 是否一致
- `changeflag.sh` 是否具备 guest flag 写入逻辑

手动增强检查使用：

```bash
bash scripts/linux_qemu_manual_check.sh --mode preflight --case-dir <linux-qemu-dir>
```

Docker build、QEMU boot、guest flag 写入和 PoC 复现必须显式选择 `--mode build|boot|flag|full`。

## 7. 自动修复

预览安全修复：

```bash
bash scripts/validate.sh --fix Dockerfile start.sh challenge.yaml
```

写入安全修复：

```bash
bash scripts/validate.sh --fix-write Dockerfile start.sh challenge.yaml
```

允许把显式 loopback 绑定参数改写为 `0.0.0.0`：

```bash
bash scripts/validate.sh --fix --fix-loopback Dockerfile start.sh challenge.yaml
```

## 8. 模板变量速查

本节承接旧版 `SKILL.md` 的统一模板变量清单。实际渲染逻辑以 `render.py`、`utils.py` 和 `templates/` 为准。

通用变量：

- `BASE_IMAGE`
- `WORKDIR`
- `APP_SRC`
- `APP_DST`
- `EXPOSE_PORTS`
- `START_CMD`
- `RUNTIME_DEPS_INSTALL`
- `COPY_APP`
- `ENV_BLOCK`
- `NPM_INSTALL_BLOCK`
- `PIP_REQUIREMENTS_BLOCK`
- `HEALTHCHECK_BLOCK`
- `STACK_FLAG_BLOCK`

Linux-QEMU 变量：

- `VM_QEMU_BINARY`
- `VM_ACCELERATOR`
- `VM_KERNEL`
- `VM_INITRD`
- `VM_ROOTFS`
- `VM_NETDEV`
- `VM_GUEST_FLAG_PATH`
- `VM_FLAG_INJECTION`
