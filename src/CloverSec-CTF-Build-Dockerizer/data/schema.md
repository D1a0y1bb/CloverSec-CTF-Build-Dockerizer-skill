# challenge.yaml 输入 Schema（v1）

本文档定义 `CloverSec-CTF-Build-Dockerizer` 的稳定输入格式。渲染器会在字段缺失时按 `data/stacks.yaml` 与 `data/patterns.yaml` 提供默认值或推断值。

## 顶层结构

```yaml
challenge:
  name: "example"
  stack: "node|php|python|java|tomcat|lamp|pwn|ai|rdg"
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
  flag:
    path: "/flag"
    permission: "444"
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
  rdg:
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
    scoring_mode: "check_service"
    include_flag_artifact: true
    check_enabled: true
    check_script_path: "check/check.sh"
  extra:
    env: { KEY: VALUE }
    copy: [{ from: "x", to: "y" }]
    user: ""
    npm_install_block: ""
    pip_requirements_block: ""
```

## 字段说明

- `challenge.name`：题目标识字符串。
- `challenge.stack`：技术栈，可选 `node/php/python/java/tomcat/lamp/pwn/ai/rdg`，缺省时自动侦测。
- `challenge.base_image`：基础镜像；为空时使用栈默认值。
- `challenge.workdir`：容器内工作目录。
- `challenge.app_src`：构建上下文内源代码路径。
- `challenge.app_dst`：镜像内应用目标路径。
- `challenge.expose_ports`：暴露端口列表，至少一个。

- `challenge.start.mode`：启动模式。
  - `cmd`：单服务前台进程。
  - `service`：服务命令模式。
  - `supervisor`：多进程编排模式。
- `challenge.start.cmd`：主启动命令。
- `challenge.start.service_name`：服务名（`mode=service` 时可用）。

- `challenge.runtime_deps`：运行期系统依赖（apt/apk）。
- `challenge.build_deps`：构建期依赖（可用于多阶段方案）。

- `challenge.flag.path`：默认 `/flag`。
- `challenge.flag.permission`：默认 `444`。

- `challenge.platform.entrypoint`：固定 `/start.sh`。
- `challenge.platform.require_bash`：固定 `true`。
- `challenge.platform.allow_loopback_bind`：默认 `false`。开启后放行 localhost/127.0.0.1 监听门禁（用于 SSRF/内网链路题型）。

- `challenge.healthcheck.enabled`：默认 `true`，控制是否渲染 Docker `HEALTHCHECK`。
- `challenge.healthcheck.cmd`：健康检查命令，默认回退 `stacks.yaml defaults.healthcheck_cmd`。
- `challenge.healthcheck.interval`：默认 `30s`。
- `challenge.healthcheck.timeout`：默认 `5s`。
- `challenge.healthcheck.retries`：默认 `3`。
- `challenge.healthcheck.start_period`：默认 `10s`。

- `challenge.rdg.enable_ttyd`：仅 `stack=rdg` 生效，默认 `true`。
- `challenge.rdg.ttyd_port`：仅 `stack=rdg` 生效，默认 `8022`。
- `challenge.rdg.ttyd_login_cmd`：仅 `stack=rdg` 生效，默认 `/bin/bash`。
- `challenge.rdg.enable_sshd`：仅 `stack=rdg` 生效，默认 `true`。
- `challenge.rdg.sshd_port`：仅 `stack=rdg` 生效，默认 `22`。
- `challenge.rdg.sshd_password_auth`：仅 `stack=rdg` 生效，默认 `true`。
- `challenge.rdg.ttyd_binary_relpath`：仅 `stack=rdg` 生效，默认 `ttyd`。
- `challenge.rdg.ttyd_install_fallback`：仅 `stack=rdg` 生效，默认 `true`。
- `challenge.rdg.ctf_user`：仅 `stack=rdg` 生效，默认 `ctf`。
- `challenge.rdg.ctf_password`：仅 `stack=rdg` 生效，默认 `123456`。
- `challenge.rdg.ctf_in_root_group`：仅 `stack=rdg` 生效，默认 `false`。
- `challenge.rdg.scoring_mode`：仅 `stack=rdg` 生效，默认 `check_service`，可选 `check_service/flag`。
- `challenge.rdg.include_flag_artifact`：仅 `stack=rdg` 生效，默认 `true`。
- `challenge.rdg.check_enabled`：仅 `stack=rdg` 生效，默认 `true`。
- `challenge.rdg.check_script_path`：仅 `stack=rdg` 生效，默认 `check/check.sh`（相对 `WORKDIR`）。
  - 脚本入口建议：`bash check/check.sh [target_ip] [target_port]`
  - 脚本返回码约定：`0=通过`、`1=失败`、`2=脚本使用/运行错误`
  - 质量门禁：占位脚本（如 `CHECK_IMPLEMENT_ME/TODO` 或短脚本直接 `exit 0`）会被 `validate.sh` 判定为 `ERROR`。

- `challenge.extra.env`：附加环境变量。
- `challenge.extra.copy`：附加复制列表。
- `challenge.extra.user`：运行用户（按题目要求启用）。
- `challenge.extra.npm_install_block`：覆盖 Node 依赖安装块。
- `challenge.extra.pip_requirements_block`：覆盖 Python 依赖安装块。

## 能力边界

- 当前支持 CTF Jeopardy 模式下的 Web/Pwn/AI 以及 RDG（Docker）容器构建。
- 当前不支持 AWD/AWDP 赛制所需的攻防编排逻辑。

## 平台硬约束

- 镜像必须包含 `/start.sh` 并可执行。
- 镜像必须包含 `/flag` 且可读（RDG 且 `include_flag_artifact=false` 时可显式关闭）。
- 镜像必须包含 `/bin/bash`。
- Dockerfile 必须包含 `EXPOSE`。
- 单服务启动必须使用 `exec` 作为 PID1。
- 禁止 `sleep infinity` 与空转循环保活。

## 示例位置

标准示例：

- `examples/node-basic/challenge.yaml`
- `examples/php-apache-basic/challenge.yaml`
- `examples/python-flask-basic/challenge.yaml`
- `examples/java-jar-basic/challenge.yaml`
- `examples/tomcat-war-basic/challenge.yaml`
- `examples/lamp-basic/challenge.yaml`
- `examples/pwn-basic/challenge.yaml`
- `examples/ai-basic/challenge.yaml`
- `examples/ai-transformers-basic/challenge.yaml`
- `examples/rdg-php-hardening-basic/challenge.yaml`
- `examples/rdg-python-ssti-basic/challenge.yaml`

兼容示例：

- `examples/node/challenge.yaml`
- `examples/php/challenge.yaml`
- `examples/python/challenge.yaml`
- `examples/java/challenge.yaml`
- `examples/tomcat/challenge.yaml`
- `examples/lamp/challenge.yaml`
