# RDG(Docker) 模板说明

## 适用场景

- RDG（Docker）模式题目交付。
- 默认双通道登录：`ttyd + sshd`。
- 默认判定链路：`check_service`（可回退为 `flag`）。
- 在平台硬约束下保持可校验、可发布。
- 默认 check 脚手架为 fail-closed：未实现时会以失败退出，避免误发布。

## 默认值

- 默认端口：`80`
- 默认工作目录：`/app`
- 默认基础镜像：`debian:bookworm-slim`
- 默认启动命令：按环境自动选择主服务的兼容回退命令
- 默认选手用户：`ctf`
- 默认口令：`123456`

## RDG 专有配置（challenge.rdg）

| 字段 | 默认值 | 说明 |
|---|---|---|
| `enable_ttyd` | `true` | 是否启用 ttyd 登录通道 |
| `ttyd_port` | `8022` | ttyd 监听端口 |
| `ttyd_login_cmd` | `/bin/bash` | ttyd 登录命令 |
| `ttyd_binary_relpath` | `ttyd` | 题目目录内 ttyd 二进制相对路径（最终落地到 `/ttyd`） |
| `ttyd_install_fallback` | `true` | ttyd 缺失时是否尝试 apt/apk 安装，且在包不可用时回退下载官方静态二进制 |
| `enable_sshd` | `true` | 是否启用 sshd 登录通道 |
| `sshd_port` | `22` | sshd 监听端口 |
| `sshd_password_auth` | `true` | 是否启用 sshd 密码认证 |
| `ctf_user` | `ctf` | 默认选手账户 |
| `ctf_password` | `123456` | 默认选手口令 |
| `ctf_in_root_group` | `false` | 是否将 ctf 用户加入 root 组 |
| `scoring_mode` | `check_service` | 判定模式：`check_service` / `flag` |
| `include_flag_artifact` | `true` | 是否保留 `/flag` 产物链路 |
| `check_enabled` | `true` | 是否启用 check 门禁约束 |
| `check_script_path` | `check/check.sh` | check 脚本路径（相对 `WORKDIR`） |

## check 脚本契约（v1.3.6）

- 建议入口：`bash check/check.sh [target_ip] [target_port]`
- 参数回退：`TARGET_IP` / `TARGET_HOST` / `TARGET_PORT`
- 返回码语义：
  - `0`：检查通过（题目已修复）
  - `1`：检查失败（漏洞仍可利用或业务异常）
  - `2`：脚本使用或运行错误
- 推荐结构：`服务可用性检查 + 漏洞负向检查（利用成功即失败）`

## 最小 challenge.yaml 示例

```yaml
challenge:
  name: rdg-basic
  stack: rdg
  base_image: php:8.2-apache
  workdir: /app
  app_src: .
  app_dst: /app
  expose_ports: ["80"]
  start:
    mode: cmd
    cmd: apache2-foreground
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
```

## 常见坑

1. `enable_ttyd=true` 但未提供题目自带 ttyd，且关闭了安装/下载回退。
2. `enable_sshd=true` 但未写入 sshd 配置或未启动 sshd。
3. `scoring_mode=check_service` 且 `check/check.sh` 缺失。
4. `check/check.sh` 仍是占位内容（`CHECK_IMPLEMENT_ME/TODO`、短脚本直接 `exit 0`），会被校验器阻断。
5. 把 `start_cmd` 写成后台命令，导致主进程退出。
