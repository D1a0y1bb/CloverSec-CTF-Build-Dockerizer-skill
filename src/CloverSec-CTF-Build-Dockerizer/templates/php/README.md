# PHP(Apache) 模板说明（最小可运行）

## 适用场景
- PHP + Apache 单服务题目。
- 默认前台命令 `apache2-foreground`，符合容器主进程模型。

## 默认约定
- 默认基础镜像：`php:8.2-apache`
- 默认工作目录：`/var/www/html`
- 默认端口：`80`
- 默认启动命令：`apache2-foreground`

## 变量说明
| 变量 | 必填 | 默认值 | 说明 |
|---|---|---|---|
| `{{BASE_IMAGE}}` | 是 | `php:8.2-apache` | 基础镜像 |
| `{{WORKDIR}}` | 是 | `/var/www/html` | 工作目录 |
| `{{APP_SRC}}` | 是 | `.` | 应用来源路径 |
| `{{APP_DST}}` | 是 | `/var/www/html` | 应用目标路径 |
| `{{EXPOSE_PORTS}}` | 是 | `80` | 暴露端口 |
| `{{START_CMD}}` | 否 | `apache2-foreground` | 启动命令，空值自动回退默认 |
| `{{ENV_BLOCK}}` | 否 | `# no docker env` / `:` | 环境变量片段 |
| `{{COPY_APP}}` | 否 | `# no extra copy` | 额外 COPY 片段 |

## 最小 challenge.yaml 示例
```yaml
challenge:
  name: "php-apache-basic"
  stack: "php"
  base_image: "php:8.2-apache"
  workdir: "/var/www/html"
  app_src: "."
  app_dst: "/var/www/html"
  expose_ports: ["80"]
  start:
    mode: "cmd"
    cmd: "apache2-foreground"
```

## php-fpm 扩展说明
- 当前模板是 Apache 分支。
- 若需要 php-fpm，可基于此目录复制出 `php-fpm` 变体：镜像改为 `php:8.2-fpm`，`start.sh` 改为 `exec php-fpm -F`。
