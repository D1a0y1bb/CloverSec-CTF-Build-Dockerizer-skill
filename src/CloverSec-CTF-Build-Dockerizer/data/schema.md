# challenge.yaml Schema (v3.0)

本文档定义 `CloverSec-CTF-Build-Dockerizer` 的稳定输入契约。

## 目录

- 顶层结构
- 关键字段说明
- 平台硬约束（V3）
- AWDP 契约
- BaseUnit 约定
- Scenario 约定（本地编排）
- 运行时档位（php/node/java）
- 参考文件

## 顶层结构

```yaml
challenge:
  name: "example"
  category: "web|pwn|ai|misc|crypto|reverse|forensics"
  stack: "node|php|python|java|tomcat|lamp|pwn|ai|rdg|secops|baseunit|bundle|linux-qemu"
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
    contract: "direct-exec-v1"
    require_bash: false
    allow_loopback_bind: false
    docker_platform: ""   # 可选，例如 linux/amd64

  healthcheck:
    enabled: true
    cmd: "bash -lc 'echo > /dev/tcp/127.0.0.1/80'"
    interval: "30s"
    timeout: "5s"
    retries: 3
    start_period: "10s"

  flag:
    mode: "direct_exec|file_replace|database|helper_script|qemu_guest"
    path: "/flag"
    initial_file: false
    permission: "444"
    update:
      command: ""
      wait_for: ""
    sync_paths: []        # 仅 legacy-helper 兼容

  verification:
    solve_probe:
      type: "http|tcp|container_exec"
      path: "/"
      expect_status: 200
      expect_text: ""

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
    initrd: "vm/initrd.img"   # 不需要 initrd 时可显式写成空字符串
    rootfs: "vm/rootfs.ext4"
    drive_format: "raw"
    append: "console=ttyS0 root=/dev/vda rw init=/sbin/init panic=-1"
    guest_forwards:
      - proto: "tcp"   # 当前版本仅支持 tcp，自 v2.1.0 起
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

  bundle:   # stack=bundle
    recipe_id: "legacy-centos7-python39-mysql57-redis5"
    mode: "single_container"
    support_level: "partial"
    services: []
    startup_order: []
    notes: []

  extra:
    env: { KEY: VALUE }
    copy: [{ from: "x", to: "y" }]
    user: ""
    npm_install_block: ""
    pip_requirements_block: ""
```

## 关键字段说明

- `challenge.stack`
  - 支持：`node/php/python/java/tomcat/lamp/pwn/ai/rdg/secops/baseunit/bundle/linux-qemu`
  - 未显式提供时可由探测规则推断。
  - `stack=bundle` 只用于 `render_bundle.py` 生成的 Recipe 交付目录；custom 组合必须显式提供安装与启动命令，不是自动安装器。

- `challenge.category`
  - 表示题目分类。它不决定 Docker 运行时。
  - Crypto、Reverse、Forensics 和附件型 Misc 可以使用 `delivery.kind=attachment-only`。

- `challenge.platform.contract`
  - 默认值为 `direct-exec-v1`。
  - 旧平台调用 `/changeflag.sh` 时显式使用 `legacy-helper-v2`。
  - Linux-QEMU 使用 `linux-qemu-v1`。

- `challenge.flag.mode`
  - `direct_exec`：平台通过 `docker exec` 写入 `flag.path`。
  - `file_replace`：在 `FLAG_UPDATE.md` 输出 `sed` 或 `echo` 命令。
  - `database`：在 `FLAG_UPDATE.md` 输出等待条件和 SQL 命令。
  - `helper_script`：显式生成 `/changeflag.sh`。
  - `qemu_guest`：使用 guest rootfs 注入流程。

- `challenge.flag.path`
  - 表示题目程序实际读取的路径。
  - `/flag` 只是默认值。
  - Pwn 题必须根据源码或题目手册确认 `/home/ctf/flag`、`flag0`、`flag1` 或其他路径。

- `challenge.flag.sync_paths`
  - 只为 `legacy-helper-v2` 保留。
  - `direct_exec` 模式应直接设置 `flag.path`，不再依赖通用同步脚本。

- `challenge.profile`
  - 支持：`jeopardy/rdg/awd/awdp/secops`
  - 默认值：
    - `stack=rdg` -> `rdg`
    - `stack=secops` -> `secops`
    - 其他 -> `jeopardy`

- `challenge.defense`（V3 推荐字段，兼容 V2 输入）
  - 用于统一防御注入配置（sshd/ttyd/ctf 用户/评分模式）。
  - 非 `rdg/secops` 栈在 `profile!=jeopardy` 且开启防御开关时会注入 defense block。
  - `stack=rdg` 与 `stack=secops` 使用专用模板语义，避免重复注入。

- `challenge.rdg`（legacy）
  - 继续兼容输入。
  - 渲染前会与 `challenge.defense` 归一化，冲突时以 `defense` 为主。

- `defense.include_flag_artifact`
  - 兼容旧 profile 的初始 flag 控制项。
  - 设为 `false` 时不生成初始 flag 文件；它不会改变 direct-exec 的运行时注入。

- `challenge.platform.docker_platform`
  - 可选字段，用于渲染 `FROM --platform=<value> ...`。
  - 常见于 Pwn 历史题迁移，例如在 macOS arm64 上固定 `linux/amd64`，避免镜像架构无提示变化。

- `challenge.flag.sync_paths`
  - 仅供 `legacy-helper-v2` 和需要多路径同步的历史题目使用。
  - direct-exec 题目应把程序实际读取路径写入 `challenge.flag.path`。

- `challenge.verification.solve_probe`
  - 可选字段，由业务断言验证入口在容器启动后执行。
  - 支持与 `smoke_assert.yaml` 相同的断言形态：`http`、`tcp`、`container_exec`。
  - 该字段用于证明“题目入口可用”，不属于 `validate.sh` 的平台契约范围。
  - 参考示例：`examples/python-flask-basic/challenge.yaml`。

- `challenge.vm`
  - 仅用于 `stack=linux-qemu`。
  - `expose_ports` 表示 Docker 容器对外端口；`vm.guest_forwards[*].host_port` 必须出现在 `expose_ports` 中。
  - `vm.guest_forwards[*].proto` 当前版本仅支持 `tcp`（自 `v2.1.0` 起）。
  - `vm.drive_format` 仅支持 `raw/qcow2`；`qemu_binary`、VM 相对路径、`guest_flag_path`、`extra_args` 会做字符级安全校验。
  - `accelerator=tcg` 是默认可移植模式；`accelerator=kvm` 或 `require_kvm=true` 需要运行平台显式提供 `/dev/kvm`。
  - `asset_mode=prebuilt` 表示题目目录已经包含 kernel/initrd/rootfs；`asset_mode=build-script` 表示构建镜像时执行 `build_script` 生成 VM 资产。
  - `flag_injection=debugfs` 会让生成的 `changeflag.sh` 同时写外层 `/flag` 和 guest rootfs 内的 `guest_flag_path`。

## 平台硬约束（V3）

每次普通题目交付必须包含：

- `Dockerfile`
- `start.sh`

并满足：

- 镜像内可执行 `/start.sh`
- Dockerfile 声明 `EXPOSE`
- 禁止空转保活（`sleep infinity` 等）

`changeflag.sh` 仅在 `flag.mode=helper_script|qemu_guest` 时要求。

`flag` 规则：

- direct-exec 通过平台运行时写入 `flag.path`。
- `flag.initial_file=false` 时不交付初始 `flag` 文件。
- `include_flag_artifact=false` 仍兼容旧 profile，并只影响初始文件。

## AWDP 契约

当最终 profile 为 `awdp` 时，输出目录必须存在：

- `patch/src/`
- 可执行 `patch/patch.sh`
- `patch_bundle.tar.gz`（包含以上两者）

## BaseUnit 约定

- `stack=baseunit` 面向“指定组件 + 指定版本”的纯服务最小单元。
- 推荐优先通过 `render_component.py` 生成，而不是手写 challenge。
- 组件定义文件：`data/components.yaml`。

## Bundle/Recipe 约定

- `stack=bundle` 面向单容器多服务交付目录。
- 推荐优先通过 `render_bundle.py` 生成，而不是手写 challenge。
- 生成的 `challenge.bundle.recipe_id`、`challenge.bundle.services` 和端口声明必须与 recipe 定义一致。
- 固定 Recipe 未覆盖时，可使用显式 custom bundle：必须提供 `base_image`、`expose_ports`、`services`、`start_commands`，可选 `install_commands`。
- 不完整组合必须返回 `BUNDLE_UNSUPPORTED_COMBINATION`，不能自动改写为其他栈。
- Bundle 输入 schema：`data/bundle_schema.md`；Recipe 定义：`data/bundle_recipes.yaml`。

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
- 镜像优先级：`--base-image > CLI --runtime-profile > challenge.base_image > challenge.runtime_profile > infer/default`

## 参考文件

- 栈默认与探测：`data/stacks.yaml`
- 推断规则：`data/patterns.yaml`
- profile 默认：`data/profiles.yaml`
- 组件定义：`data/components.yaml`
- 场景规则：`data/scenario_schema.md`
- 场景校验规则：`data/validate_scenario_rules.yaml`
- 可配置校验：`data/validate_rules.yaml`
