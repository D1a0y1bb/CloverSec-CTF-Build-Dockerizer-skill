# 各语言 Dockerfile / start.sh 范例

照这些写法改成题目实际的版本、端口和命令。

## 目录

- 镜像版本固定
- Python（Flask / gunicorn）
- Node
- PHP（cli 内置服务器）
- PHP-FPM + nginx
- Java（jar / 多阶段编译）
- 纯静态
- Pwn（socat / xinetd）
- 国内构建与 CRLF

---

## 镜像版本固定

同一份源码过段时间再构建就失败，通常是构建输入变了：浮动 tag、没锁时间点的 apt 源、PECL/pip 装到了新版本。

普通题目用 `python:3.11-slim` 这样的 tag 即可。漏洞只在特定版本成立（某个 ImageMagick、Redis 或库的 CVE），或者题目要长期存档时，按下面四步锁定：

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

从旧镜像或 rootfs 恢复题目时，先查出原来的版本再锁定：

```bash
docker run --rm --entrypoint sh <旧镜像> -c '
  uname -m; cat /etc/os-release | head -2
  php -v; php -r "echo phpversion(\"imagick\"), PHP_EOL;"; convert -version | head -1
  redis-server --version; java -version 2>&1 | head -1; catalina.sh version 2>/dev/null | grep "Server number"
  dpkg -l 2>/dev/null | grep -E "imagemagick|libmagick|redis|mysql|mariadb" '
```

只有 rootfs 时，看 `etc/os-release`、`var/lib/dpkg/status`、`usr/local/lib/php/extensions/` 和 `/opt` 下的目录名。查到的版本在 Dockerfile 里锁定，旁边注释写来源：

```dockerfile
# 版本取自原题镜像：漏洞依赖 imagick 3.7.0 + Redis 6.0.8
RUN pecl install imagick-3.7.0
```

不要把旧版本的包装到新的基础镜像上，例如旧 `libxml2-dev` 配新基础镜像自带的 `libxml2` 会依赖冲突。基础镜像、apt 源和包版本锁到同一个时间点。

---

## Python（Flask / gunicorn）

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY src/ /app/
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
# 单 worker：题目状态存在进程内存里，多 worker 之间不共享。
exec gunicorn -w 1 -b 0.0.0.0:5000 app:app
```

小题也可以 `exec python app.py`，app 里要监听 `0.0.0.0`。

---

## Node

```dockerfile
FROM node:20-alpine

WORKDIR /app
COPY src/ /app/
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

## PHP（cli 内置服务器）

```dockerfile
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

## PHP-FPM + nginx

```dockerfile
FROM php:8.1-fpm-alpine

# 题目的解法依赖 pcntl_fork + pcntl_exec 绕过 disable_functions，必须编译 pcntl。
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
# nginx 通过 127.0.0.1:9000 转发给 php-fpm，先起 fpm 再起 nginx。
php-fpm --nodaemonize &
nginx -t
exec nginx -g 'daemon off;'
```

---

## Java（jar / 多阶段编译）

有现成 jar：

```dockerfile
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

从源码编译时用多阶段构建，运行镜像里不带 maven：

```dockerfile
FROM maven:3.9-eclipse-temurin-17 AS build
WORKDIR /build
COPY src/pom.xml ./pom.xml
COPY src/src ./src
RUN mvn -q -DskipTests package

FROM eclipse-temurin:17-jre
COPY --from=build /build/target/app.jar /app/app.jar
COPY start.sh /start.sh
COPY flag /flag
RUN chmod 555 /start.sh && chmod 444 /flag
EXPOSE 8080
CMD ["/start.sh"]
```

---

## 纯静态

```dockerfile
FROM nginx:alpine
COPY src/ /usr/share/nginx/html/
COPY start.sh /start.sh
COPY flag /flag
RUN chmod 555 /start.sh && chmod 444 /flag
EXPOSE 80
```

```bash
#!/bin/sh
exec nginx -g 'daemon off;'
```

平台用 `/start.sh` 覆盖 `CMD`，静态题也要有 start.sh。

---

## Pwn（socat / xinetd）

发给选手的二进制和镜像里运行的必须是同一个文件，否则选手本地算出的偏移在远程不成立。直接 `COPY` 现成二进制，不要在镜像里重新编译。

### socat

```dockerfile
FROM ubuntu:22.04

RUN apt-get update && apt-get install -y --no-install-recommends socat \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -m ctf

COPY src/pwn /home/ctf/pwn
# Flag 属主 root:ctf、权限 440：题目进程以 ctf 运行，能读不能改。
COPY flag /home/ctf/flag
RUN chown root:ctf /home/ctf/pwn /home/ctf/flag \
    && chmod 550 /home/ctf/pwn \
    && chmod 440 /home/ctf/flag

COPY start.sh /start.sh
RUN chmod 555 /start.sh

EXPOSE 10000
CMD ["/start.sh"]
```

```bash
#!/bin/sh
cd /home/ctf
# 不加 pty：pty 会把 0x7f、0x03 等字节当成控制字符处理，payload 里的地址会被改掉。
exec socat TCP-LISTEN:10000,reuseaddr,fork EXEC:/home/ctf/pwn,su=ctf,stderr
```

程序里要 `setvbuf(stdout, NULL, _IONBF, 0)`，否则没有 pty 时输出会被缓冲，选手看不到提示。源码不在手里时用 `stdbuf -o0 /home/ctf/pwn`。

### xinetd

旧题和很多外部题用 xinetd + chroot，迁移时保留原写法即可：

```text
service ctf
{
    disable     = no
    socket_type = stream
    protocol    = tcp
    wait        = no
    user        = root
    type        = UNLISTED
    port        = 10000
    bind        = 0.0.0.0
    server      = /usr/sbin/chroot
    server_args = --userspec=1000:1000 /home/ctf ./pwn
    per_source  = 10
    rlimit_cpu  = 20
}
```

```bash
#!/bin/sh
exec /usr/sbin/xinetd -dontfork
```

chroot 到 `/home/ctf` 后，程序依赖的 `lib`、`lib64`、`bin/sh` 要提前拷进 `/home/ctf`。`flag.path` 写容器里的真实路径 `/home/ctf/flag`，程序里读的是 chroot 后的 `/flag`。

---

## 国内构建与 CRLF

- 基础镜像拉不下来时加镜像前缀，例如 `docker.m.daocloud.io/library/php:7.4-cli`。手册里写清原始镜像名，方便在别处构建。
- apt 慢可以换 `mirrors.aliyun.com`，换源只改 `sources.list`，不要顺手升级系统包。
- Windows 上编辑过的 start.sh 可能是 CRLF，容器里会报 `bad interpreter`。直接把文件转成 LF；`verify.sh` 会检查这一项。
