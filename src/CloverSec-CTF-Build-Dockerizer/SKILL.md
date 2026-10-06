---
name: cloversec-ctf-build-dockerizer
description: 四叶草安全-创研中心竞赛题目容器构建 Skill。把一个题目想法、半成品源码或参考目录，整理成干净、可读、可构建、可验证的 CTF 题目交付目录（src/ + Dockerfile + start.sh + challenge.yaml）。适用于 Web/Pwn/AI/Misc 等常规 Docker 题目；多服务、Bundle、Scenario、RDG/AWD、Linux-QEMU 等特殊形态按需查阅 references。
metadata:
  short-description: 把题目想法或源码整理成干净可验证的 Docker 题目目录
allowed-tools:
  - Bash
  - Read
  - Write
  - Glob
  - Grep
---

# CloverSec CTF Build Dockerizer

## 交付什么

给你一个题目想法、一段参考代码或一个乱目录，产出一个**你自己一眼能看懂**的题目目录：源码整洁、注释到位、能 `docker build`、能起服务、能被平台写入动态 Flag。

你（模型）负责写代码和组织目录。脚本只在最后做真实验证。不要让工具链替你决定题目长什么样。

## 默认目录

```text
<题目名>/
├── src/              # 题目源码、静态资源、二进制
├── Dockerfile        # 镜像构建入口
├── start.sh          # 前台拉起真实服务
├── challenge.yaml    # 平台合同（最小字段）
├── .dockerignore
└── flag              # 仅当服务启动前需要初始 flag 文件时保留
```

只放运行需要的东西。题解、抓包、手册、`__pycache__`、`.DS_Store`、打包产物不进交付目录。

## 怎么做

1. **读事实。** 先看懂已有的 `Dockerfile`、`start.sh`、`challenge.yaml`、源码入口、依赖文件（`requirements.txt`/`package.json`/...）和题目手册里写的运行方式、端口、Flag 路径。已有的就用，别重写。
2. **写/整理源码。** 把业务代码组织进 `src/`，命名清晰、分层简单。缺的部分你来补全，让题目能真正跑起来。
3. **写 Dockerfile 和 start.sh。** 照着下面"参考范例"的风格：短、真实、每条非显然的指令配一句中文注释说明原因。
4. **写 challenge.yaml。** 只填平台需要的字段（见下）。
5. **验证。** `docker build` → `docker run` 起容器 → `docker exec` 写一个测试 flag → curl/nc 打一遍入口，确认题目真能解。用 `scripts/verify.sh` 跑这一套。

缺端口、启动命令、运行时或真实 Flag 路径这类**会卡住构建**的信息时，一次性只问真正缺的那几项，不要猜。

## 参考范例（这就是"好的样子"）

一个单进程 PHP 题的 Dockerfile 应该像这样——紧凑，注释讲"为什么"：

```dockerfile
# syntax=docker/dockerfile:1
FROM php:8.1-fpm-alpine

# 题目核心：disable_functions 禁掉了常见命令执行函数，但 pcntl 没禁，
# 所以必须把 pcntl 编译进去，解题链才成立。
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

对应的 start.sh——讲清启动顺序，`exec` 主进程做 PID 1：

```bash
#!/bin/bash
set -euo pipefail

# php-fpm 只绑回环，对外由 nginx 转发；先拉起 fpm 再起 nginx。
php-fpm --nodaemonize &
nginx -t
exec nginx -g 'daemon off;'
```

更多栈（Node/Python/Java/纯静态/Pwn）的范例见 `references/dockerfiles.md`。

如果题目对运行时版本敏感（漏洞只在特定版本成立），或者要长期存档复现，就要把基础镜像、apt 包、PECL/pip 依赖锁死版本，否则以后 build 会因上游漂移而打不通——锁版本的具体手法见 `references/dockerfiles.md` 的"镜像版本固定"一节。

## 中文注释规范

交付的代码**必须有中文注释**，但只注释不明显的东西：

- **业务源码**：讲清漏洞点在哪、这段逻辑为什么这么写、关键分支的意图。
- **Dockerfile**：解释每个非显然的决定（为什么装这个扩展、为什么锁这个版本、平台约束）。
- **start.sh**：解释启动顺序、等待条件、异常处理。

不要写这种注释（它们就是"东坡肉"）：

```bash
: # defense block disabled          # ← 空操作 + 无意义说明
# no extra copy                     # ← 描述"没做什么"
RUN set -eux; \                     # ← 整段空块
    :
cd /app  # 切换到 /app 目录          # ← 复读下一行代码
```

一句话：注释解释**原因**，不复读代码，不记录"没做什么"，不写版本变更史。

## Flag 合同

平台在容器启动后，直接把动态 Flag 写进程序真正读取的那个文件。你只需要在 `challenge.yaml` 里写对路径：

```yaml
flag:
  path: /flag          # 程序实际读取的路径，比如 /var/www/html/flag.php
  permission: "444"
```

- Flag 文件由 Dockerfile `COPY flag /flag` 放入并设为可读，start.sh 不碰它。
- 文件替换 / 数据库这类特殊写入方式，在手册或 `references/platform.md` 里记真实命令即可，不要造通用脚本。
- 平台的 helper 脚本只在旧平台或 Linux-QEMU 这类特殊合同下才需要，见 `references/special.md`。

## challenge.yaml 最小字段

```yaml
challenge:
  name: afterimage
  stack: php                       # php / node / python / java / static / c ...
  base_image: php:8.1-fpm-alpine
  workdir: /var/www/html
  app_src: src
  app_dst: /var/www/html
  expose_ports: ["80"]
  start:
    mode: cmd
    cmd: "nginx -g 'daemon off;'"
  platform:
    entrypoint: /start.sh
  flag:
    path: /flag
    permission: "444"
```

字段含义见 `references/platform.md`。

## 验证

```bash
bash scripts/verify.sh <题目目录>
```

它会真实构建镜像、起容器、写一个测试 flag、探测入口，然后清理。结果如实报告：

- `passed`：构建、启动、Flag 回读、入口探测都过了。
- `partial`：部分过，还有没验的（说清是哪项）。
- `failed`：构建或运行失败。
- `unverified`：缺信息没法验，别假装过了。

静态检查通过 ≠ 题目可解。能起、能改 Flag、入口能打通，才算数。

## 少见情况按需查

只有输入确实是这种形态，或用户明确要求时，再读对应参考：

| 情况 | 参考 |
|---|---|
| 多服务 / docker-compose / Vulhub-like | `references/special.md` |
| Bundle / BaseUnit 组合环境 | `references/special.md` |
| Scenario 多阶段编排 | `references/special.md` |
| RDG / AWD / AWDP / SecOps | `references/special.md` |
| Linux kernel / QEMU guest 题 | `references/special.md` |
| 旧平台 helper（changeflag 等历史交付） | `references/special.md` |

常规单服务题不要去读这些，也不要把多服务题悄悄压成单服务。
