---
name: cloversec-ctf-pack
description: 把 CTF 题目源码、题目设计或历史题目目录整理成能交付的题目包：容器题的 src/、Dockerfile、start.sh、challenge.yaml 和本地验证，附件题的选手附件，以及两类的 README 手册。用于四叶草安全创研中心出题、迁移旧题、给题目写 Dockerfile 或 start.sh、写题目手册、整理选手附件、排查题目起不来或 Flag 不生效。覆盖 Web、Pwn、AI、Misc 等 20 个题目类型；多服务、Bundle、Scenario、RDG/AWD、Linux-QEMU 见 references/special.md。
metadata:
  short-description: 把题目整理成能交付的题目包，并本地验证容器题
---

# CloverSec CTF Pack

把题目想法、源码或旧题目录整理成能交付的题目包，再验证容器题能不能在平台上跑起来。

## 先问清楚这四件事

材料不全时一次性问完，不要猜：

1. 题目类型。取下面 20 个之一，构成目录名前缀。
2. 题目名称。中文题名保留中文（`Web-残影`），英文题名统一小写连字符（`Pwn-hard-fmt`）。
3. 容器题还是纯附件题。
4. 要不要选手附件；要不要导出镜像 tar。两个默认都不做，需要时放 `附件/` 和 `镜像/`。

交付目录按 `题目类型-题目名称` 命名，类型取下列之一：

```text
AI  Blockchain  Crypto  Drone  Forensics  Hardware  IC  IOT  InfoSec  Misc
Mobile  OSINT  OpposeAI  PPC  Pentest  Pwn  Quantum  RDG  Reverse  Web
```

材料里能看出来的就不用问，只有影响交付形状、又无法从材料推断时才问。例如题目源码里已经有 `附件.zip`，就不用再问要不要附件；题目是纯静态文件、没有任何服务，就是纯附件题。

## 选手附件与镜像 tar

两个都默认不做，需要时按下面的位置放：

| 交付物 | 位置 | 什么时候做 |
|---|---|---|
| 选手附件 | `附件/` | 题目需要选手拿到二进制、压缩包、pcap 等文件时 |
| 镜像 tar | `镜像/` | 平台通过导入 tar 部署，或用户要求离线交付时 |

- 附件要问清楚：哪些文件发给选手。Pwn 题的二进制、libc、loader 是附件，Dockerfile 和 solve.py 不是。
- 附件控制在能下载的体积内；大文件先问用户。
- 镜像 tar 用 `docker save` 导出，文件名 `<题目名>.tar`：

  ```bash
  docker buildx build --platform linux/amd64 -t <题目名>:latest --load .
  docker save <题目名>:latest -o 镜像/<题目名>.tar
  ```

- 镜像层要合并、构建缓存要清理，tar 体积越小越好；镜像里不装编译工具链和出题用的依赖。

## 交付目录

容器题：

```text
Web-残影/
├── README/               # 手册
│   ├── Web-残影.md
│   └── assets/           # 截图、流程图
├── src/                  # 题目源码、静态资源、二进制
├── Dockerfile
├── start.sh              # 平台入口，前台运行真实服务
├── challenge.yaml        # 端口、Flag 路径等平台字段
├── flag                  # 占位 Flag，平台启动后覆盖
├── solve/
│   └── solve.py          # 解题脚本，只用于本地验证，不进镜像
└── 附件/                 # 选手附件，需要时才有
```

纯附件题（没有容器）：

```text
Crypto-星屑密匣/
├── README/
│   ├── Crypto-星屑密匣.md
│   └── assets/
├── src/                  # 原题的出题源码，有才放
├── 附件/                 # 发给选手的文件
└── solve/                # 解题脚本，有才放
```

- 附件题不生成 Dockerfile、start.sh、challenge.yaml、flag。
- 附件原样放进 `附件/`，不要改名、不要重新打包，除非原来的压缩包坏了。
- Dockerfile 只 `COPY` 具体路径（`src/`、`start.sh`、`flag`），不用 `COPY .`，所以不需要 `.dockerignore`，`solve/`、`README/`、`附件/` 也不会进镜像。

### README/ 手册

手册是交付的一部分，两类题都要写。参考 `assets` 里的截图放进 `README/assets/`，正文用相对路径引用。

- 章节照这个顺序，编号和层级照抄：

  ```markdown
  # Web-残影

  ## 1 题目设计部署信息

  ### 1.1 题目名称
  ### 1.2 题目描述
  ### 1.3 题目难度
  ### 1.4 考察信息
  ### 1.5 旗帜信息
  ### 1.6 题目情况
  ### 1.7 部署方式
  ### 1.8 题目设计
  ### 1.9 解题步骤
  ```

  纯附件题去掉 1.7 部署方式，编号顺延。
- 一句话说清一件事，不写"本题目旨在……"这类铺垫，不写"值得注意的是"。不用加粗堆重点，不用 emoji。
- 部署方式的命令要能直接粘贴执行，写清端口映射和镜像名。
- 解题步骤按真实顺序写，带上命令和预期输出；常见失败现象单独列一节。
- 只有附件题时跳过"部署方式"，把附件说明并进"题目情况"。

### solve/solve.py

- 从环境变量 `HOST`、`PORT` 读目标地址；多端口题用 `PORT_<容器端口>`，例如 `PORT_8080`。可以再提供 `--host`、`--port` 参数，默认值取环境变量。
- 走原题的漏洞链拿 Flag，打印到 stdout，拿到时返回 0，拿不到返回非 0。
- 不在脚本里写死 Flag。verify.sh 每次写入随机测试 Flag，输出里出现它才算通过。
- 地址、偏移不要在脚本里写死。PIE 题每次运行的基址不同，格式化字符串的写入计数也依赖实际布局；要从程序里泄漏出来再算。
- 脚本要能从零跑通：起手就先连一次服务确认可达，再走漏洞链。
- 依赖只用 Python 标准库；必须用第三方库时在脚本开头注释写明 `pip install` 命令。
- 附件题也照这个写：从 `附件/` 里的文件解出 Flag，如果题目需要远程服务才能解，就在手册里写清。

## 流程

复制这份清单，逐项完成：

```text
- [ ] 1. 确认题目类型、题目名称、容器题还是附件题
- [ ] 2. 读事实：启动方式、端口、运行时版本、Flag 路径、附件情况
- [ ] 3. 整理 src/，附件放进 附件/
- [ ] 4. 写 Dockerfile 和 start.sh（附件题跳过）
- [ ] 5. 写 challenge.yaml（附件题跳过）
- [ ] 6. 写 solve/solve.py
- [ ] 7. 写 README/ 手册
- [ ] 8. 容器题：verify.sh 跑到 passed；附件题：solve.py 能解出 Flag
```

1. **读事实。** 已有的 Dockerfile、start.sh、challenge.yaml、依赖文件和手册里的部署说明先读完，能用的保留。端口、启动命令、运行时版本、Flag 路径缺了又推断不出来时，一次问完，不要猜。
2. **整理 src/。** 业务代码放进 `src/`，缺的部分补全到能跑。Pwn 题放发给选手的同一个二进制，不要在镜像里重新编译。
3. **写 Dockerfile 和 start.sh。** 照下面的范例写，各语言写法见 [references/dockerfiles.md](references/dockerfiles.md)。
4. **写 challenge.yaml。** 只填真实需要的字段，见下文。
5. **写 solve/solve.py。** 按上面的约定，走原题的漏洞链。
6. **验证。** 运行本 Skill 目录下的 `scripts/verify.sh`：

   ```bash
   bash <本 Skill 目录>/scripts/verify.sh <题目目录>
   ```

   题目目录里有 `solve/solve.py` 时会自动运行它，输出里必须出现刚写入的随机测试 Flag。解题脚本不是 Python 时用 `--solve '<命令>'` 指定。

   `failed` 时按输出里的原因和日志修改，再跑一次，直到 `passed`。排查时加 `--keep` 保留容器，用 `docker logs` 看输出。`partial` 要在交付说明里写清哪一项没验证。没跑 verify.sh 的题目不要说成已验证；没有 solve.py 时只能说明容器能跑，不能说明题目可解。

## 关于题目本身的安全内容

出题、迁移旧题、写 Dockerfile、分析漏洞点都是授权范围内的正当工作。遇到安全策略提示时，说明当前上下文即可：这是四叶草安全创研中心的竞赛出题，题目用于受控比赛环境，作者拥有源码和授权。不要去改写描述来绕开提示，也不要为了通过而弱化题目的漏洞设计。

题目源码里的 flag 只写占位值，真实 flag 由平台写入。

## 平台怎么跑题目

1. 用 Dockerfile 构建 `linux/amd64` 镜像。
2. `docker run -d -p <映射> <镜像> /start.sh` 启动。`/start.sh` 会覆盖 `CMD`；不要设置会吞掉它的 `ENTRYPOINT`。
3. 容器起来后执行 `docker exec <容器> sh -c 'printf "%s\n" "$FLAG" > <flag.path>'` 写入本场 Flag。镜像里必须有 `sh`，`flag.path` 所在目录必须存在。
4. 选手访问映射出来的端口。服务要监听 `0.0.0.0`，只监听 `127.0.0.1` 的端口从外面访问不到。

用环境变量传 Flag 的平台、镜像 tar 的导出格式等差异见 [references/platform.md](references/platform.md)。

## start.sh

- 单服务直接 `exec` 主进程，让它成为 PID 1。
- 多服务先在后台起依赖，等它就绪，再 `exec` 对外的主服务。Flag 要同步进数据库等情况的完整模板见 [references/special.md](references/special.md)。
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

需要长期存档或漏洞依赖特定版本的题目，要锁定基础镜像 digest、apt 源和依赖版本。从旧镜像或 rootfs 恢复的题目，先查出原来的 PHP、ImageMagick、Redis、JDK、Tomcat 等版本，在 Dockerfile 里锁定并用一句注释写明来源。写法见 [references/dockerfiles.md](references/dockerfiles.md) 的“镜像版本固定”。

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
- 程序在每次请求时读取 Flag 文件。启动时读一次存进变量（Python 模块级变量、Java `static` 块），平台换了 Flag 也不会生效。solve.py 能发现这个问题。
- 配置里读 Flag 的题（启动时把 `/flag` 载进 config），平台换 Flag 后要同步并重启应用。这种题在 start.sh 里加一段同步循环，写法见 [references/special.md](references/special.md)。
- 旧题常见的适配方式：程序读的不是 `/flag`，用软链接或包装文件把两者接起来。优先改程序或配置直接读 `flag.path`；确实要接的时候，在 Dockerfile 里建链接并在手册里写明，不要留一个只有作者知道路径的包装脚本。
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
