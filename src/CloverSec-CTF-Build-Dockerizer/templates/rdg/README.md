# RDG(Docker) 模板说明

## 适用场景

- RDG（Docker）模式题目交付。
- 兼容题目主服务 + ttyd 旁路调试链路。
- 在平台硬约束下保持可校验、可发布。

## 默认值

- 默认端口：`80`
- 默认工作目录：`/app`
- 默认基础镜像：`debian:bookworm-slim`
- 默认启动命令：按环境自动选择主服务的兼容回退命令

## RDG 专有配置（challenge.rdg）

| 字段 | 默认值 | 说明 |
|---|---|---|
| `enable_ttyd` | `true` | 是否尝试启动 ttyd 旁路（找不到二进制仅 WARN） |
| `ttyd_port` | `8022` | ttyd 监听端口 |
| `ttyd_login_cmd` | `/bin/bash` | ttyd 登录命令 |

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
```

## 常见坑

1. 把 `start_cmd` 写成后台命令，导致主进程退出。
2. 题目依赖 ttyd 但镜像内没有 ttyd 二进制。
3. 服务仅监听 `127.0.0.1`，导致映射端口不可达。
