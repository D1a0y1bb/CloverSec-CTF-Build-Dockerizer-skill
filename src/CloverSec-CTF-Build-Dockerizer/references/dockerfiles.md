# 各栈 Dockerfile / start.sh 范例

照抄这些风格：短、真实、注释讲原因。把其中的版本、端口、命令换成你题目实际需要的。

通用原则：
- 单进程题：`start.sh` 直接 `exec` 主进程，让它当 PID 1。
- 多进程题：后台起依赖服务，前台 `exec` 对外主进程。
- 能用官方/国内镜像源就用，按需换 `base_image`。
- 只装题目真正用到的依赖。

---

## 镜像版本固定（题目要存档、以后还要能复现时）

真实教训：同一份源码"以前能 build、过段时间再 build 就不通"，根因通常不是源码被改，而是**构建输入会漂移**——用了浮动 tag、apt 源没锁时间点、PECL/pip 装的是最新版。等上游更新，依赖版本对不上，题目行为就变了。

普通题目用 `python:3.11-slim` 这种 tag 就够了。但如果这道题**对运行时版本敏感**（漏洞只在特定版本成立，比如某个 ImageMagick / Redis / 库的 CVE），或者要**长期存档复现**，就要把构建输入锁死：

1. **基础镜像锁 digest**，不只用 tag：

   ```dockerfile
   FROM php:8.2.29-apache-bookworm@sha256:bb954ec03238abf760e91a3fa74202f192d644be12bd4bda5bac577997a76466
   ```

2. **Debian/apt 源锁到 snapshot 时间点**，并关掉有效期检查：

   ```dockerfile
   RUN printf '%s\n' \
       'Types: deb' \
       'URIs: http://snapshot.debian.org/archive/debian/20251117T000000Z' \
       'Suites: bookworm' 'Components: main' \
       'Signed-By: /usr/share/keyrings/debian-archive-keyring.gpg' \
       > /etc/apt/sources.list.d/debian.sources; \
       echo 'Acquire::Check-Valid-Until false;' > /etc/apt/apt.conf.d/99snapshot
   ```

3. **apt 包锁具体版本号**：

   ```dockerfile
   RUN apt-get update && apt-get install -y --no-install-recommends \
       imagemagick=8:6.9.11.60+dfsg-1.6+deb12u4 \
       redis-server=5:7.0.15-1~deb12u6
   ```

4. **PECL/源码包锁版本 + 校验 SHA256**：

   ```dockerfile
   RUN wget -O /tmp/imagick.tgz https://pecl.php.net/get/imagick-3.8.0.tgz; \
       echo 'bda67461c854f20d6105782b769c524fc37388b75d4481d951644d2167ffeec6  /tmp/imagick.tgz' | sha256sum -c -; \
       pecl install /tmp/imagick.tgz
   ```

一个反向教训：**不要把旧版本包硬拼到新基础镜像上**（旧 `libxml2-dev` 配新基础层的 `libxml2` 会依赖冲突）。要锁就整套锁到同一个时间点基线，保证内部一致。

> 固定版本会让 Dockerfile 变长，这是必要的，不算"东坡肉"——它是题目能不能复现的关键。但不敏感的普通题目别过度固定，`python:3.11-slim` 就行。

---

## Python（Flask / gunicorn）

```dockerfile
# syntax=docker/dockerfile:1
FROM python:3.11-slim

WORKDIR /app
COPY src/ /app/
# 先装依赖再拷代码本可分层加速，这里题目小，直接一起拷即可。
RUN pip install --no-cache-dir -r requirements.txt

COPY start.sh /start.sh
COPY flag /flag
RUN chmod 555 /start.sh && chmod 444 /flag

EXPOSE 5000
CMD ["/start.sh"]
```

```bash
#!/bin/sh
set -eu
cd /app
# 监听 0.0.0.0，容器外才可达；单 worker 便于题目状态可控。
exec gunicorn -w 1 -b 0.0.0.0:5000 app:app
```

小题直接 `exec python app.py` 也可以，只要 app 里监听 `0.0.0.0`。

---

## Node（Express / 原生 http）

```dockerfile
# syntax=docker/dockerfile:1
FROM node:20-alpine

WORKDIR /app
COPY src/ /app/
# 有 lock 用 ci 保证可复现，没有就 install。
RUN if [ -f package-lock.json ]; then npm ci --omit=dev; else npm install --omit=dev; fi

COPY start.sh /start.sh
COPY flag /flag
RUN chmod 555 /start.sh && chmod 444 /flag

EXPOSE 3000
CMD ["/start.sh"]
```

```bash
#!/bin/sh
set -eu
cd /app
exec node server.js
```

---

## PHP（cli 内置服务器，适合小题）

```dockerfile
# syntax=docker/dockerfile:1
FROM php:7.4-cli

WORKDIR /var/www/html
COPY src/ /var/www/html/
COPY start.sh /start.sh
COPY flag /flag
RUN chmod 555 /start.sh && chmod 444 /flag

EXPOSE 5000
CMD ["/start.sh"]
```

```bash
#!/bin/sh
set -eu
cd /var/www/html
exec php -S 0.0.0.0:5000 -t /var/www/html
```

---

## PHP-FPM + nginx（标准 Web 题，多进程）

```dockerfile
# syntax=docker/dockerfile:1
FROM php:8.1-fpm-alpine

# 题目核心：disable_functions 禁了常见命令执行函数但漏了 pcntl，
# 解题链依赖 pcntl_fork+pcntl_exec，所以必须把 pcntl 编译进来。
RUN set -eux; \
    apk add --no-cache nginx bash; \
    docker-php-ext-install pcntl

COPY nginx/nginx.conf /etc/nginx/nginx.conf
WORKDIR /var/www/html
COPY src/ /var/www/html/

COPY start.sh /start.sh
COPY flag /flag
RUN chmod 555 /start.sh && chmod 444 /flag

EXPOSE 80
CMD ["/start.sh"]
```

```bash
#!/bin/bash
set -euo pipefail
# php-fpm 只绑回环，对外由 nginx 转发；先起 fpm 再起 nginx。
php-fpm --nodaemonize &
nginx -t                       # 配置自检，坏了立刻暴露
exec nginx -g 'daemon off;'
```

---

## Java（Spring Boot 等，jar 包）

有现成 jar 直接拷：

```dockerfile
# syntax=docker/dockerfile:1
FROM eclipse-temurin:17-jre

WORKDIR /app
COPY src/app.jar /app/app.jar
COPY start.sh /start.sh
COPY flag /flag
RUN chmod 555 /start.sh && chmod 444 /flag

EXPOSE 8080
CMD ["/start.sh"]
```

```bash
#!/bin/sh
set -eu
exec java -jar /app/app.jar
```

需要从源码编译用多阶段：`maven` 阶段编译，运行阶段只拿 jar，镜像不带编译工具链。多模块题目可以每个模块一个 build 阶段：

```dockerfile
# syntax=docker/dockerfile:1
FROM maven:3.9-eclipse-temurin-17 AS build
WORKDIR /build
COPY src/pom.xml ./pom.xml
COPY src/src ./src
RUN mvn -q -DskipTests package

FROM tomcat:9.0-jdk17-temurin
COPY --from=build /build/target/app.jar /opt/app/app.jar
COPY start.sh /start.sh
COPY flag /flag
RUN chmod 555 /start.sh && chmod 444 /flag
EXPOSE 8080
CMD ["/start.sh"]
```

---

## 纯静态（nginx 托管）

```dockerfile
# syntax=docker/dockerfile:1
FROM nginx:alpine
COPY src/ /usr/share/nginx/html/
COPY flag /flag
RUN chmod 444 /flag
EXPOSE 80
# nginx 官方镜像自带前台入口，静态题可不写 start.sh。
```

---

## C / Pwn（TCP 服务，socat 转发）

```dockerfile
# syntax=docker/dockerfile:1
FROM ubuntu:22.04

# build-essential 包含 gcc + libc-dev 头文件，只装 gcc 会缺 stdio.h 编译报错。
# socat 负责每个连接 fork 一个题目进程。
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential socat \
    && rm -rf /var/lib/apt/lists/*

# Pwn 题约定：flag 放在 /home/ctf/flag，以 ctf 用户运行，隔离选手的读写权限。
RUN useradd -m ctf

COPY src/pwn.c /home/ctf/pwn.c
# -fno-stack-protector -no-pie：关掉栈保护和地址随机化，让 ret2win 地址固定可预测。
RUN gcc -o /home/ctf/pwn /home/ctf/pwn.c \
        -fno-stack-protector -no-pie -z execstack \
    && chmod 555 /home/ctf/pwn \
    && rm /home/ctf/pwn.c

COPY flag /home/ctf/flag
RUN chmod 444 /home/ctf/flag && chown ctf:ctf /home/ctf/flag

COPY start.sh /start.sh
RUN chmod 555 /start.sh

EXPOSE 10000
CMD ["/start.sh"]
```

```bash
#!/bin/sh
set -eu
# 每个连接 fork 一个题目进程，以 ctf 用户运行，互相隔离。
exec socat TCP-LISTEN:10000,reuseaddr,fork \
     EXEC:"su ctf -s /bin/sh -c /home/ctf/pwn",pty,stderr
```

Pwn 题的 `flag.path` 固定是 `/home/ctf/flag`，不是 `/flag`——平台也往这个路径写。有时也见 `/root/flag`（主机安全/应急响应类题），按题目程序真实读取的路径来写。

如果已有编译好的二进制，把 `COPY src/pwn.c` + `RUN gcc` 换成 `COPY src/pwn /home/ctf/pwn` 即可，不需要装 `build-essential`（只装 `socat`）。
