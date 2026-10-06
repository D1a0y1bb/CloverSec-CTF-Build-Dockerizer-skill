---
name: cloversec-ctf-build-dockerizer
description: 把 CTF 题目源码、题目设计或历史题目目录整理成竞赛平台能直接导入的 Docker 题目目录（src/、Dockerfile、start.sh、challenge.yaml），并在本机构建、以 /start.sh 启动、写入测试 Flag、探测端口来验证。用于四叶草安全创研中心出题、迁移旧题、给题目写 Dockerfile 或 start.sh、排查题目起不来或 Flag 不生效。覆盖 Web、Pwn、AI、Misc；多服务、Bundle、Scenario、RDG/AWD、Linux-QEMU 见 references/special.md。
metadata:
  short-description: 把题目源码整理成能上平台的 Docker 题目目录并本地验证
---

# CloverSec CTF Build Dockerizer

把题目想法、源码或旧题目录整理成平台能直接导入的容器题目录。源码、Dockerfile、start.sh 由你按下面的范例编写，`scripts/verify.sh` 按平台的方式把题目跑一遍。

## 交付目录

```text
<题目名>/
├── src/              # 题目源码、静态资源、二进制
├── Dockerfile
├── start.sh          # 平台入口，前台运行真实服务
├── challenge.yaml    # 端口、Flag 路径等平台字段
├── .dockerignore
└── flag              # 占位 Flag，平台启动后覆盖
```

只放运行需要的文件。题解、exp、抓包、出题手册、镜像 tar、`__pycache__`、`.DS_Store` 不放进这个目录。

## 流程

复制这份清单，逐项完成：

```text
- [ ] 1. 读事实：启动方式、端口、运行时版本、Flag 路径
- [ ] 2. 整理 src/
- [ ] 3. 写 Dockerfile 和 start.sh
- [ ] 4. 写 challenge.yaml
- [ ] 5. verify.sh 跑到 passed
```

1. **读事实。** 已有的 Dockerfile、start.sh、challenge.yaml、依赖文件和手册里的部署说明先读完，能用的保留。端口、启动命令、运行时版本、Flag 路径缺了又推断不出来时，一次问完，不要猜。
2. **整理 src/。** 业务代码放进 `src/`，缺的部分补全到能跑。Pwn 题放发给选手的同一个二进制，不要在镜像里重新编译。
3. **写 Dockerfile 和 start.sh。** 照下面的范例写，各语言写法见 [references/dockerfiles.md](references/dockerfiles.md)。
4. **写 challenge.yaml。** 只填真实需要的字段，见下文。
5. **验证。** 运行本 Skill 目录下的 `scripts/verify.sh`：

   ```bash
   bash <本 Skill 目录>/scripts/verify.sh <题目目录>
   # 有解题脚本时加上，脚本从环境变量 HOST、PORT 读目标地址
   bash <本 Skill 目录>/scripts/verify.sh <题目目录> --solve 'python3 solve.py'
   ```

   `failed` 时按输出里的原因和日志修改，再跑一次，直到 `passed`。`partial` 要在交付说明里写清哪一项没验证。没跑 verify.sh 的题目不要说成已验证。

## 平台怎么跑题目

1. 用 Dockerfile 构建 `linux/amd64` 镜像。
2. `docker run -d -p <映射> <镜像> /start.sh` 启动。`/start.sh` 会覆盖 `CMD`；不要设置会吞掉它的 `ENTRYPOINT`。
3. 容器起来后执行 `docker exec <容器> sh -c 'printf "%s\n" "$FLAG" > <flag.path>'` 写入本场 Flag。镜像里必须有 `sh`，`flag.path` 所在目录必须存在。
4. 选手访问映射出来的端口。服务要监听 `0.0.0.0`，只监听 `127.0.0.1` 的端口从外面访问不到。

用环境变量传 Flag 的平台、镜像 tar 的导出格式等差异见 [references/platform.md](references/platform.md)。

## start.sh

- 单服务直接 `exec` 主进程，让它成为 PID 1。
- 多服务先在后台起依赖，等它就绪，再 `exec` 对外的主服务。
- 旧题常见 `service xxx start` 加 `tail -f /dev/null` 保活，平台能跑，但服务挂掉后容器不会退出，平台仍显示正常。新写的题用 `exec`，迁移旧题时能改就改。
- 不在 start.sh 里创建、覆盖或 chmod Flag 文件。
- 换行符用 LF，第一行写 shebang；用到 bash 语法就写 `#!/bin/bash` 并确认镜像里装了 bash。

## 参考范例

单容器 PHP-FPM + nginx 的 Dockerfile：

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

对应的 start.sh：

```bash
#!/bin/bash
set -euo pipefail

# nginx 通过 127.0.0.1:9000 转发给 php-fpm，先起 fpm 再起 nginx。
php-fpm --nodaemonize &
nginx -t
exec nginx -g 'daemon off;'
```

需要长期存档或漏洞依赖特定版本的题目，要锁定基础镜像 digest、apt 源和依赖版本，写法见 [references/dockerfiles.md](references/dockerfiles.md) 的“镜像版本固定”。

## 中文注释

交付的代码要有中文注释，只写不明显的内容：

- 业务源码：漏洞点在哪，关键分支为什么这样写。
- Dockerfile：为什么装这个扩展、为什么锁这个版本、平台有什么约束。
- start.sh：启动顺序、等待条件。

以下注释不要写：

```bash
: # defense block disabled          # 空操作
# no extra copy                     # 描述没做的事
cd /app  # 切换到 /app 目录          # 复读代码
```

## Flag

`challenge.yaml` 的 `flag.path` 必须是程序实际读取的文件：

| 题型 | 常用路径 |
|---|---|
| Web / AI / Misc | `/flag` |
| Pwn | `/home/ctf/flag`，属主 `root:ctf`，权限 `440` |
| PHP 嵌入 Flag | `/var/www/html/flag.php` |
| 数据库 | 手册里写清更新 Flag 的 SQL |

- Dockerfile 用 `COPY flag <flag.path>` 放占位文件。
- 程序在每次请求时读取 Flag 文件。启动时读一次存进变量（Python 模块级变量、Java `static` 块），平台换了 Flag 也不会生效。`verify.sh --solve` 能发现这个问题。
- 文件替换、数据库这类写入方式，把平台要执行的命令写进手册，见 [references/platform.md](references/platform.md)。

## challenge.yaml

```yaml
challenge:
  name: afterimage
  stack: php                       # php / node / python / java / static / pwn
  base_image: php:8.1-fpm-alpine
  expose_ports: ["80"]
  platform:
    entrypoint: /start.sh
  flag:
    path: /flag
    permission: "444"
```

完整字段见 [references/platform.md](references/platform.md)。

## 特殊题型

输入确实是下面这些形态，或用户明确要求时，读 [references/special.md](references/special.md)：

- 多服务、docker-compose、Vulhub 类环境
- Bundle、BaseUnit 组合环境
- Scenario 多阶段编排
- RDG、AWD、AWDP、SecOps
- Linux kernel、QEMU guest
- 依赖 `changeflag.sh` 的旧平台题目

常规单服务题不读这个文件，也不要把多服务题压成单服务。
