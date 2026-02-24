# LAMP 模板说明（最小可运行）

## 适用场景
- 需要 PHP + MariaDB 的传统 Web 题目。
- 启动策略是 MariaDB 后台运行，Apache 前台 `exec`。

## 默认约定
- 默认基础镜像：`debian:bookworm-slim`
- 默认工作目录：`/var/www/html`
- 默认端口：`80`
- 默认启动命令：`apache2ctl -D FOREGROUND`

## 变量说明
| 变量 | 必填 | 默认值 | 说明 |
|---|---|---|---|
| `{{BASE_IMAGE}}` | 是 | `debian:bookworm-slim` | 基础镜像 |
| `{{WORKDIR}}` | 是 | `/var/www/html` | 工作目录 |
| `{{APP_SRC}}` | 是 | `.` | 应用来源路径 |
| `{{APP_DST}}` | 是 | `/var/www/html` | 应用目标路径 |
| `{{EXPOSE_PORTS}}` | 是 | `80` | 暴露端口 |
| `{{START_CMD}}` | 否 | `apache2ctl -D FOREGROUND` | 前台主服务命令 |
| `{{ENV_BLOCK}}` | 否 | `# no docker env` / `:` | 环境变量片段 |
| `{{COPY_APP}}` | 否 | `# no extra copy` | 额外 COPY 片段 |

## 可选数据库初始化
- 支持环境变量 `MYSQL_INIT_SQL_B64`（base64 编码 SQL）。
- `start.sh` 在数据库可用后执行一次该 SQL。

## 最小 challenge.yaml 示例
```yaml
challenge:
  name: "lamp-basic"
  stack: "lamp"
  base_image: "debian:bookworm-slim"
  workdir: "/var/www/html"
  app_src: "."
  app_dst: "/var/www/html"
  expose_ports: ["80"]
  start:
    mode: "cmd"
    cmd: "apache2ctl -D FOREGROUND"
```
