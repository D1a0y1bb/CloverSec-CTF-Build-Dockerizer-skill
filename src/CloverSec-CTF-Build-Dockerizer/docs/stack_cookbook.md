# 技术栈手册（v2.1.0）

本手册给出各栈最小配置与 V2 使用建议。

## 全局规则

- 所有栈最终交付都必须包含：`Dockerfile/start.sh/changeflag.sh`
- 默认要求 `/flag`；仅在受支持的 defense profile 显式设置 `include_flag_artifact=false` 时可放行
- profile 推荐通过 `challenge.profile` 显式声明
- 防御配置使用 `challenge.defense`；`challenge.rdg` 仅兼容输入

## 支持栈

- `node`
- `php`
- `python`
- `java`
- `tomcat`
- `lamp`
- `pwn`
- `ai`
- `rdg`
- `secops`
- `linux-qemu`
- `baseunit`

## 通用最小片段

```yaml
challenge:
  name: demo
  stack: node
  profile: jeopardy
  base_image: node:20-alpine
  workdir: /app
  app_src: .
  app_dst: /app
  expose_ports: ["3000"]
  start:
    mode: cmd
    cmd: "node server.js"
```

## profile/defense 示例

```yaml
challenge:
  stack: node
  profile: awd
  defense:
    enable_ttyd: true
    ttyd_port: "8022"
    enable_sshd: true
    sshd_port: "22"
    ctf_user: "ctf"
    ctf_password: "123456"
    scoring_mode: "check_service"
    include_flag_artifact: true
    check_enabled: true
    check_script_path: "check/check.sh"
```

## stack=rdg 建议

- 使用 `profile=rdg`
- 保持 `check/check.sh` 为真实检查脚本（避免占位实现）
- 当题目不需要静态 `/flag` 且当前 profile/stack 已支持该放行语义时，可设置 `include_flag_artifact=false`

## stack=secops 建议

- 使用 `profile=secops`
- 常见题型：nginx/redis/mysql/ssh 配置加固
- 可通过 `scoring_mode=check_service` + `check/check.sh` 实施策略检查

## stack=baseunit 建议

- 优先用 `render_component.py` 按组件+版本生成
- 首批组件：mysql/redis/sshd/ttyd/apache/nginx/tomcat/php-fpm/vsftpd/weblogic
- 示例：

```bash
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/render_component.py \
  --component mysql \
  --variant 8.0-debian \
  --output /tmp/baseunit-mysql
```

## stack=linux-qemu 建议

- 面向 Linux kernel CVE/LPE 题目，外层 Docker 仍按平台契约启动 `/start.sh`，漏洞内核运行在 QEMU guest 中。
- 默认使用 `accelerator=tcg`；只有平台明确允许 `/dev/kvm` 时才配置 `kvm` 或 `require_kvm=true`。
- `expose_ports` 表示 Docker 容器端口，`vm.guest_forwards[*].host_port` 必须与它一致；`v2.1.0` 仅支持 TCP 转发。
- 动态 flag 若需要 guest 内可读，使用 `flag_injection=debugfs` 并设置 `guest_flag_path`。

```yaml
challenge:
  name: linux-qemu-basic
  stack: linux-qemu
  profile: jeopardy
  base_image: debian:bookworm-slim
  workdir: /opt/linux-qemu
  expose_ports: ["22"]
  start:
    mode: cmd
    cmd: qemu-system-x86_64
  vm:
    arch: x86_64
    accelerator: tcg
    memory: 768M
    cpus: 2
    kernel: vm/vmlinuz
    initrd: vm/initrd.img
    rootfs: vm/rootfs.ext4
    guest_forwards:
      - proto: tcp
        host_port: "22"
        guest_port: "22"
    guest_flag_path: /root/flag
    flag_injection: debugfs
```

## scenario（本地编排）

- 用 `scenario.yaml` 描述多服务
- 用 `render_scenario.py` 生成 `docker-compose.yml`
- 用 `validate_scenario.py` 校验
- 注意：compose 仅本地验证，平台最终仍是单服务交付

## AWDP 契约提示

profile 为 `awdp` 的服务必须包含：

- `patch/src/`
- 可执行 `patch/patch.sh`
- `patch_bundle.tar.gz`

## 运行时档位（php/node/java）

- 推断：`derive_config.py`
- 显式选择：`render.py --runtime-profile <id>`
- 优先级：`--base-image > --runtime-profile > challenge.base_image > 推断`
