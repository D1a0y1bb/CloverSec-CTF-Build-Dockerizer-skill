# 技术栈手册（v2.2.0）

本手册给出各栈最小配置与 V2 使用建议。

## 目录

- 全局规则
- 支持栈
- 12 栈最小模板库索引
- 通用最小片段
- profile/defense 示例
- stack=rdg 建议
- stack=secops 建议
- stack=baseunit 建议
- stack=linux-qemu 建议
- scenario（本地编排）
- AWDP 契约提示
- 运行时档位（php/node/java）

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

## 12 栈最小模板库索引

本节承接旧版 `SKILL.md` 中的栈模板索引。更详细的模板实现以 `templates/<stack>/` 和 `data/stacks.yaml` 为准。

### Node

- 适用：Node 原生 HTTP、Express、Koa、Fastify。
- 默认端口：`3000`。
- 默认启动命令：`node server.js`。
- 可选启动：`npm run start`、`pm2-runtime app.js`。
- 模板：`templates/node/Dockerfile.tpl`、`templates/node/start.sh.tpl`。

### PHP (Apache)

- 适用：传统 PHP 站点和轻量 PHP 框架。
- 默认端口：`80`。
- 默认启动命令：`apache2-foreground`。
- php-fpm 分支不作为默认渲染路径。
- 模板：`templates/php/Dockerfile.tpl`、`templates/php/start.sh.tpl`。

### Python

- 适用：Flask、FastAPI、Django、自写 HTTP。
- 默认端口：`5000`。
- 默认启动命令：`python app.py`。
- 可选启动：`gunicorn -b 0.0.0.0:5000 app:app`、`uvicorn app:app --host 0.0.0.0 --port 5000`。
- 模板：`templates/python/Dockerfile.tpl`、`templates/python/start.sh.tpl`。

### Java (JAR)

- 适用：已有可运行 `app.jar`。
- 默认端口：`8080`。
- 默认启动命令：`java -jar app.jar`。
- 可选启动：`java -Xms128m -Xmx256m -jar app.jar`。
- 模板：`templates/java/Dockerfile.tpl`、`templates/java/start.sh.tpl`。

### Tomcat (WAR)

- 适用：已有 WAR 包部署。
- 默认端口：`8080`。
- 默认启动命令：`catalina.sh run`。
- 多 WAR 场景可复制整个 `webapps` 目录。
- 模板：`templates/tomcat/Dockerfile.tpl`、`templates/tomcat/start.sh.tpl`。

### LAMP

- 适用：同容器内需要 Apache + PHP + MariaDB。
- 默认端口：`80`。
- 默认启动命令：`apache2ctl -D FOREGROUND`。
- 最小启动范式：后台启动 MariaDB，前台 `exec apache2ctl -D FOREGROUND`。
- 可用 `MYSQL_INIT_SQL_B64` 注入初始化 SQL。
- 模板：`templates/lamp/Dockerfile.tpl`、`templates/lamp/start.sh.tpl`。

### Pwn (xinetd/tcpserver/socat)

- 适用：Jeopardy 二进制远程交互题。
- 默认端口：`10000`。
- 默认启动命令：`/usr/sbin/xinetd -dontfork`。
- Alpine 可回退 `tcpserver`，缺失时回退 `socat`。
- 默认建议设置 `platform.docker_platform: linux/amd64`，避免在 arm64 主机上生成架构不符合原题的镜像。
- 可通过 `flag.sync_paths` 把平台动态 flag 同步到题目业务路径，例如 `/home/ctf/flag`、`/home/ctf/flag0`、`/home/ctf/flag1`。
- `sync_paths` 需要平台调用 `/changeflag.sh` 后生效；源码里读 `flag0/flag1`、数据库或环境变量时，仍要人工确认真实路径和验证方式。
- 模板：`templates/pwn/Dockerfile.tpl`、`templates/pwn/start.sh.tpl`。

### Linux-QEMU

- 适用：Linux kernel CVE/LPE 题目。
- 默认端口：`22`。
- 默认 QEMU binary：`qemu-system-x86_64`。
- 默认加速器：`tcg`。
- 默认 guest flag 路径：`/root/flag`。
- QEMU 参数由 `challenge.vm` 结构化生成。
- 可选：`accelerator=auto`、`asset_mode=build-script`、`flag_injection=none`。
- 模板：`templates/linux-qemu/Dockerfile.tpl`、`templates/linux-qemu/start.sh.tpl`。

### AI (CPU)

- 适用：CTF AI Web 题目和 CPU 推理场景。
- 默认端口：`5000`。
- 默认启动命令：`gunicorn -w 1 --threads 1 -b 0.0.0.0:5000 app:app`。
- 需要限制 `OPENBLAS/OMP/MKL` 等线程数。
- 示例：`ai-basic`、`ai-transformers-basic`。
- 模板：`templates/ai/Dockerfile.tpl`、`templates/ai/start.sh.tpl`。

### RDG (Docker)

- 适用：防御修复型 Docker 题目，通常使用 check-service 判定。
- 默认端口：业务端口 + `22` + `8022`。
- 双通道启用时，后台拉起 `sshd` 和 `ttyd`，前台 `exec` 业务主服务。
- `include_flag_artifact=false` 可用于仅 check-service 判定。
- `check_enabled=true` + `check_script_path` 会启用 check 脚本门禁。
- 模板：`templates/rdg/Dockerfile.tpl`、`templates/rdg/start.sh.tpl`。

### SecOps

- 适用：安全运维类配置加固题，例如 nginx、redis、mysql、ssh、tomcat。
- 推荐：`stack=secops` + `profile=secops`。
- 判定方式：`scoring_mode=check_service` + `check/check.sh`。
- 模板：`templates/secops/Dockerfile.tpl`、`templates/secops/start.sh.tpl`。

### BaseUnit

- 适用：指定服务包/指定版本的纯基座最小镜像单元。
- 推荐通过 `render_component.py` 按 `component+variant` 生成。
- 首批组件：`mysql/redis/sshd/ttyd/apache/nginx/tomcat/php-fpm/vsftpd/weblogic`。
- 模板：`templates/baseunit/Dockerfile.tpl`、`templates/baseunit/start.sh.tpl`。

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
python3 scripts/render_component.py \
  --component mysql \
  --variant 8.0-debian \
  --output /tmp/baseunit-mysql
```

## stack=linux-qemu 建议

- 面向 Linux kernel CVE/LPE 题目，外层 Docker 仍按平台契约启动 `/start.sh`，漏洞内核运行在 QEMU guest 中。
- 默认使用 `accelerator=tcg`；只有平台明确允许 `/dev/kvm` 时才配置 `kvm` 或 `require_kvm=true`。
- `expose_ports` 表示 Docker 容器端口，`vm.guest_forwards[*].host_port` 必须与它一致；当前版本仅支持 TCP 转发（自 `v2.1.0` 起）。
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
- 优先级：`--base-image > CLI --runtime-profile > challenge.base_image > challenge.runtime_profile > 推断`
