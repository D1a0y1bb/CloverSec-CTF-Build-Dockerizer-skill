# 技术栈配置手册（Stack Cookbook）

本文档提供 9 个技术栈的最小可用配置、常见变更和注意事项。

## 目录

1. Node
2. PHP (Apache)
3. Python
4. Java (JAR)
5. Tomcat (WAR)
6. LAMP
7. Pwn (xinetd)
8. AI (CPU)
9. RDG (Docker)

---

## 1) Node

最小 challenge.yaml 片段：

```yaml
challenge:
  stack: "node"
  base_image: "node:20-alpine"
  workdir: "/app"
  app_src: "."
  app_dst: "/app"
  expose_ports: ["3000"]
  start:
    mode: "cmd"
    cmd: "node server.js"
```

常见变更：

- 若依赖原生模块，切换 `node:20-slim`。
- 若使用 pnpm/yarn，可在 `extra.npm_install_block` 覆盖安装块。

常见错误：

- 只监听 `127.0.0.1` 导致端口不通。
- start 命令为空或文件名写错。

---

## 2) PHP (Apache)

最小 challenge.yaml 片段：

```yaml
challenge:
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

常见变更：

- 需要扩展时可在 Dockerfile 模板中安装具体 `php-*` 扩展包。
- 若改成 php-fpm，请改模板分支并保持前台运行模式。

常见错误：

- 误用 `apache2ctl start` 导致后台化，容器退出。

---

## 3) Python

最小 challenge.yaml 片段：

```yaml
challenge:
  stack: "python"
  base_image: "python:3.11-slim"
  workdir: "/app"
  app_src: "."
  app_dst: "/app"
  expose_ports: ["5000"]
  start:
    mode: "cmd"
    cmd: "python app.py"
```

常见变更：

- Gunicorn：`gunicorn -b 0.0.0.0:5000 app:app`
- Uvicorn：`uvicorn app:app --host 0.0.0.0 --port 5000`

常见错误：

- 忘记 `pip --no-cache-dir`。
- 应用只监听 `127.0.0.1`。

---

## 4) Java (JAR)

最小 challenge.yaml 片段：

```yaml
challenge:
  stack: "java"
  base_image: "eclipse-temurin:17-jre-jammy"
  workdir: "/app"
  app_src: "."
  app_dst: "/app"
  expose_ports: ["8080"]
  start:
    mode: "cmd"
    cmd: "java -jar app.jar"
```

常见变更：

- JVM 参数：`java -Xms128m -Xmx256m -jar app.jar`
- 增加 `JAVA_TOOL_OPTIONS` 环境变量。

常见错误：

- JAR 路径与 `WORKDIR` 不一致。
- 交付了源码但没有可运行 JAR。

---

## 5) Tomcat (WAR)

最小 challenge.yaml 片段：

```yaml
challenge:
  stack: "tomcat"
  base_image: "tomcat:9.0-jre17-temurin-jammy"
  workdir: "/usr/local/tomcat"
  app_src: "ROOT.war"
  app_dst: "/usr/local/tomcat/webapps/ROOT.war"
  expose_ports: ["8080"]
  start:
    mode: "cmd"
    cmd: "catalina.sh run"
```

常见变更：

- 多应用部署可改为复制整个 webapps 目录。
- 自定义 server.xml/context.xml 可通过 `extra.copy` 注入。

常见错误：

- WAR 放错目录，应用无法加载。
- 使用 `catalina.sh start` 导致容器前台进程缺失。

---

## 6) LAMP

最小 challenge.yaml 片段：

```yaml
challenge:
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

常见变更：

- 若需要数据库初始化：注入 `MYSQL_INIT_SQL_B64`。
- 若必须暴露 3306，可追加 `expose_ports: ["80", "3306"]`。

常见错误：

- 数据库未启动导致页面 500。
- 多服务都后台化，容器直接退出。

---

## 7) Pwn (xinetd)

最小 challenge.yaml 片段：

```yaml
challenge:
  stack: "pwn"
  base_image: "debian:bookworm-slim"
  workdir: "/home/ctf"
  app_src: "."
  app_dst: "/home/ctf"
  expose_ports: ["10000"]
  start:
    mode: "cmd"
    cmd: "/usr/sbin/xinetd -dontfork"
```

常见变更：

- 使用 `ctf.xinetd` 明确端口、二进制路径和资源限制。
- 题目若读取 `/home/ctf/flag`，在 `start.sh` 中增加 `/flag` 同步逻辑。

常见错误：

- 使用 `xinetd` 后台模式导致容器退出。
- `ctf.xinetd` 端口与 Dockerfile `EXPOSE` 不一致。

---

## 8) AI (CPU)

最小 challenge.yaml 片段：

```yaml
challenge:
  stack: "ai"
  base_image: "python:3.11-slim"
  workdir: "/app"
  app_src: "."
  app_dst: "/app"
  expose_ports: ["5000"]
  start:
    mode: "cmd"
    cmd: "gunicorn -w 1 --threads 1 -b 0.0.0.0:5000 app:app"
```

常见变更：

- 轻量模式使用 Flask/FastAPI + gunicorn。
- 增强模式引入 transformers，但仍建议单 worker/单线程起步。
- 在高核心宿主机设置 `OPENBLAS/OMP/MKL/NUMEXPR/GOTO=1`。

常见错误：

- 启动命令只监听 `127.0.0.1`。
- 未设置线程限制导致 OpenBLAS 线程初始化失败。

---

## 9) RDG (Docker)

最小 challenge.yaml 片段：

```yaml
challenge:
  stack: "rdg"
  base_image: "php:8.2-apache"
  workdir: "/app"
  app_src: "."
  app_dst: "/app"
  expose_ports: ["80", "22", "8022"]
  start:
    mode: "cmd"
    cmd: "apache2-foreground"
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

常见变更：

- PHP 题目可用 `apache2-foreground`，Python 题目可用 `python app.py`。
- 运维类题目若不需要登录通道，可设置 `rdg.enable_ttyd: false` 且 `rdg.enable_sshd: false`。
- `ttyd` 默认优先使用题目目录中的 `ttyd` 二进制，缺失时按 `ttyd_install_fallback` 先尝试包管理安装，再回退下载官方静态二进制。
- 默认判定是 `check_service`，需提供 `check/check.sh`（或自定义 `check_script_path`）。

常见错误：

- `enable_ttyd=true` 但镜像中未形成 `/ttyd` 可执行文件。
- `enable_sshd=true` 但未安装/启动 sshd。
- `scoring_mode=check_service` 但缺少 `check/check.sh`。
- `start.cmd` 使用后台命令导致容器主进程退出。

---

## 快速选型建议

- 纯脚本服务：Node/Python
- PHP 页面或小框架：PHP (Apache)
- 已有 JAR：Java
- 已有 WAR：Tomcat
- 必须同容器 DB：LAMP
- 二进制远程交互题：Pwn (xinetd)
- AI Web 推理题：AI (CPU)
- RDG Docker 模式题目：RDG (Docker)

## 关联文档

- 平台契约：`src/CloverSec-CTF-Build-Dockerizer/docs/platform_contract.md`
- 故障排查：`src/CloverSec-CTF-Build-Dockerizer/docs/troubleshooting.md`
