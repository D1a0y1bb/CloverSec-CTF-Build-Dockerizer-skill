# challenge.yaml Schema (v2.2.0)

本文档定义 `CloverSec-CTF-Build-Dockerizer` 的稳定输入契约。

## 目录

- 顶层结构
- 关键字段说明
- 平台硬约束（V2）
- AWDP 契约
- BaseUnit 约定
- Scenario 约定（本地编排）
- 运行时档位（php/node/java）
- 参考文件

## 顶层结构

```yaml
challenge:
  name: "example"
  stack: "node|php|python|java|tomcat|lamp|pwn|ai|rdg|secops|baseunit|linux-qemu"
  profile: "jeopardy|rdg|awd|awdp|secops"

  base_image: ""
  workdir: "/app"
  app_src: "."
  app_dst: "/app"

  expose_ports: ["80"]
  start:
    mode: "cmd|service|supervisor"
    cmd: "node server.js"
    service_name: ""

  runtime_deps: []
  build_deps: []

  platform:
    entrypoint: "/start.sh"
    require_bash: true
    allow_loopback_bind: false

  healthcheck:
    enabled: true
    cmd: "bash -lc 'echo > /dev/tcp/127.0.0.1/80'"
    interval: "30s"
    timeout: "5s"
    retries: 3
    start_period: "10s"

  flag:
    path: "/flag"
    permission: "444"

  vm:   # stack=linux-qemu
    arch: "x86_64"
    qemu_binary: "qemu-system-x86_64"
    machine: "q35"
    accelerator: "tcg|kvm|auto"
    require_kvm: false
    cpu: "max"
    memory: "768M"
    cpus: 2
    kernel: "vm/vmlinuz"
    initrd: "vm/initrd.img"
    rootfs: "vm/rootfs.ext4"
    drive_format: "raw"
    append: "console=ttyS0 root=/dev/vda rw init=/sbin/init panic=-1"
    guest_forwards:
      - proto: "tcp"   # current release supports tcp only, introduced in v2.1.0
        host_port: "22"
        guest_port: "22"
    monitor: "none"
    extra_args: ""
    asset_mode: "prebuilt|build-script"
    build_script: "scripts/build-vm.sh"
    guest_flag_path: "/root/flag"
    flag_injection: "debugfs|none"
    healthcheck_mode: "tcp|ssh-banner|ssh-auth-denied|custom"

  defense:
    enable_ttyd: true
    ttyd_port: "8022"
    ttyd_login_cmd: "/bin/bash"
    enable_sshd: true
    sshd_port: "22"
    sshd_password_auth: true
    ttyd_binary_relpath: "ttyd"
    ttyd_install_fallback: true
    ctf_user: "ctf"
    ctf_password: "123456"
    ctf_in_root_group: false
    scoring_mode: "check_service|flag"
    include_flag_artifact: true
    check_enabled: true
    check_script_path: "check/check.sh"

  rdg:   # legacy compatibility input
    ...  # same shape as defense

  extra:
    env: { KEY: VALUE }
    copy: [{ from: "x", to: "y" }]
    user: ""
    npm_install_block: ""
    pip_requirements_block: ""
```

## 关键字段说明

- `challenge.stack`
  - 支持：`node/php/python/java/tomcat/lamp/pwn/ai/rdg/secops/baseunit/linux-qemu`
  - 未显式提供时可由探测规则推断。

- `challenge.profile`
  - 支持：`jeopardy/rdg/awd/awdp/secops`
  - 默认值：
    - `stack=rdg` -> `rdg`
    - `stack=secops` -> `secops`
    - 其他 -> `jeopardy`

- `challenge.defense`（V2 推荐字段）
  - 用于统一防御注入配置（sshd/ttyd/ctf 用户/评分模式）。
  - 非 `rdg/secops` 栈在 `profile!=jeopardy` 且开启防御开关时会注入 defense block。
  - `stack=rdg` 与 `stack=secops` 使用专用模板语义，避免重复注入。

- `challenge.rdg`（legacy）
  - 继续兼容输入。
  - 渲染前会与 `challenge.defense` 归一化，冲突时以 `defense` 为主。

- `defense.include_flag_artifact`
  - 默认 `true`。
  - 设为 `false` 时仅放行 `/flag` 产物，不放行 `/changeflag.sh`。

- `challenge.vm`
  - 仅用于 `stack=linux-qemu`。
  - `expose_ports` 表示 Docker 容器对外端口；`vm.guest_forwards[*].host_port` 必须出现在 `expose_ports` 中。
  - `vm.guest_forwards[*].proto` 当前版本仅支持 `tcp`（自 `v2.1.0` 起）。
  - `vm.drive_format` 仅支持 `raw/qcow2`；`qemu_binary`、VM 相对路径、`guest_flag_path`、`extra_args` 会做字符级安全校验。
  - `accelerator=tcg` 是默认可移植模式；`accelerator=kvm` 或 `require_kvm=true` 需要运行平台显式提供 `/dev/kvm`。
  - `asset_mode=prebuilt` 表示题目目录已经包含 kernel/initrd/rootfs；`asset_mode=build-script` 表示构建镜像时执行 `build_script` 生成 VM 资产。
  - `flag_injection=debugfs` 会让生成的 `changeflag.sh` 同时写外层 `/flag` 和 guest rootfs 内的 `guest_flag_path`。

## 平台硬约束（V2）

每次渲染交付必须包含：

- `Dockerfile`
- `start.sh`
- `changeflag.sh`

并满足：

- 镜像内可执行 `/start.sh`、`/changeflag.sh`
- 镜像内存在 `/bin/bash`
- Dockerfile 声明 `EXPOSE`
- 禁止空转保活（`sleep infinity` 等）

`flag` 规则：

- 默认必须存在且可读
- `include_flag_artifact=false` 可放行 `flag`，但不能放行 `changeflag.sh`

## AWDP 契约

当最终 profile 为 `awdp` 时，输出目录必须存在：

- `patch/src/`
- 可执行 `patch/patch.sh`
- `patch_bundle.tar.gz`（包含以上两者）

## BaseUnit 约定

- `stack=baseunit` 面向“指定组件 + 指定版本”的纯服务最小单元。
- 推荐优先通过 `render_component.py` 生成，而不是手写 challenge。
- 组件定义文件：`data/components.yaml`。

## Scenario 约定（本地编排）

- 场景输入：`scenario.yaml`
- 渲染脚本：`scripts/render_scenario.py`
- 校验脚本：`scripts/validate_scenario.py`
- 生成 `docker-compose.yml` 仅用于本地验证，不是平台最终交付。

## 运行时档位（php/node/java）

- 数据源：`data/runtime_profiles.yaml`
- `derive_config.py` 会输出：
  - `runtime_profile_candidates`
  - `recommended_profile`
  - `recommended_base_image`
  - `runtime_profile_evidence`
- `render.py` 支持 `--runtime-profile <id>`。
- 镜像优先级：`--base-image > --runtime-profile > challenge.base_image > infer/default`

## 参考文件

- 栈默认与探测：`data/stacks.yaml`
- 推断规则：`data/patterns.yaml`
- profile 默认：`data/profiles.yaml`
- 组件定义：`data/components.yaml`
- 场景规则：`data/scenario_schema.md`
- 场景校验规则：`data/validate_scenario_rules.yaml`
- 可配置校验：`data/validate_rules.yaml`
