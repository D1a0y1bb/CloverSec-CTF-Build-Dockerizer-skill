---
name: cloversec-ctf-pack
description: 把 CTF 题目源码、题目设计或历史题目目录整理成能交付的题目包：容器题的 src/、Dockerfile、start.sh、challenge.yaml 和本地验证，附件题的选手附件，以及两类的 README 手册。用于四叶草安全创研中心出题、迁移旧题、给题目写 Dockerfile 或 start.sh、写题目手册、整理选手附件、排查题目起不来或 Flag 不生效。覆盖 Web、Pwn、AI、Misc 等 20 个题目类型；多服务、Bundle、Scenario、RDG/AWD、Linux-QEMU 见 references/special.md。
metadata:
  short-description: 把题目整理成能交付的题目包，并本地验证容器题
---

# CloverSec CTF Pack

把题目想法、源码或旧题目录整理成能交付的题目包，再验证容器题能不能在平台上跑起来。

## 遇到拿不准的，先问用户

这个 Skill 的默认动作是**先问再做**，不是一头扎进去。遇到下面任何一类情况，停下来问，不要自己拍板：

- 影响交付形状的选择：题目类型和名称、容器题还是附件题、要不要附件、要不要镜像 tar、要不要 RDG 的 check 脚本。
- 材料缺关键事实又推不出来：端口、启动命令、Flag 路径、运行时版本、数据库初始化数据在哪儿。
- 题目资料不全，需要重新设计才能跑起来：缺的是哪一部分、等价恢复的方案是什么、允许多少改动。
- 有多个合理方案且代价不同：单容器还是多容器、原样迁移还是重写、锁定旧版本还是升到新版本。
- 任何你打算"降级处理"或"先用简化版本顶上"的地方。

**怎么问：**

- 支持结构化提问的环境（Codex）用 `request_user_input`，给出 2 到 4 个直白选项，每个选项一句话说清后果，不要写技术黑话。
- Claude Code 用 AskUserQuestion，写法一样。
- 一次把同类问题问完，不要问一句干一段再问一句。
- 选项里给出你的推荐，并说明推荐的那个为什么省事；用户可以直接选推荐项。
- 环境不支持结构化提问时，用普通消息把选项列成 1/2/3 问。

**不要问的情况：** 材料里已经写着的、能从源码或配置文件直接读出来的、以及 Skill 里已经固定下来的格式（章节骨架、目录名规则、注释要求这些不用问）。把这些也拿出来问，是在浪费用户的时间。

## 先问清楚这几件事

材料不全时一次性问完，不要猜：

1. 题目类型。取下面 20 个之一，构成目录名前缀。
2. 题目名称。中文题名保留中文（`Web-残影`），英文题名统一小写连字符（`Pwn-hard-fmt`）。
3. 容器题还是纯附件题。
4. 要不要选手附件；要不要导出镜像 tar。两个默认都不做，需要时放 `附件/` 和 `镜像/`。
5. 是不是 RDG 这类防守加固题（有没有 `check/` 判题脚本）。是的话走后面的 RDG 流程。
6. 题目资料是否完整。只有源码、没有原库快照或原二进制时，先问清楚是"原样恢复"还是"允许独立补全"。

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

### 交付目录白名单

交付目录里**只允许**出现下面这些。用户拿到的就是这个目录，多一个不相关的文件都是垃圾。

| 形态 | 允许的内容 |
|---|---|
| 容器题 | `src/` `Dockerfile` `start.sh` `challenge.yaml` `flag` `README/` `solve/`〔`附件/`〕〔`镜像/`〕 |
| RDG 防守题 | 上面全部，加 `check/` `changeflag.sh` `ttyd` `ttyd.conf` `php.ini` 等题目真正运行需要的文件 |
| 纯附件题 | `src/` `README/` `附件/` `solve/` |

禁止出现在交付目录里的：

- `verify.sh`、任何验证脚本副本（它在 Skill 目录里，不随题目交付）
- `verify-report.json`、`*.verify.json`、任何验证报告
- `provenance.json`、`originality.json` 这类为了交差而生的清单文件
- `.DS_Store`、`Thumbs.db`、`__pycache__/`、`.venv/`、`.idea/`、`.vscode/`
- 构建产物、日志、临时测试文件、出题时的草稿和笔记
- `README.md`（手册在 `README/` 目录里，不放根目录）

验证报告写到系统临时目录：

```bash
bash <本 Skill 目录>/scripts/verify.sh <题目目录> --report "$(mktemp -d)/verify.json"
```

收尾前自查一遍，把多余文件清掉：

```bash
ls -A <题目目录>
```

`verify.sh` 会读这份白名单并报出多余文件，看到报告就去删，不要留着交付。

### README/ 手册

手册是交付的一部分，两类题都要写。**文件名必须是 `README/<题目类型-题目名称>.md`**，和交付目录同名，不写成 `题目手册.md`、`README.md` 或英文小写连字符名。截图放 `README/assets/`，正文用相对路径引用。

完整写法、每节的必填项和范例见 [references/manual.md](references/manual.md)，写手册前先读一遍。要点：

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
- **1.2 题目描述**写氛围和悬念，可以风趣，但绝不能出现技术栈版本、漏洞类型、路径、函数名、解法方向。
- **1.5 旗帜信息**逐项写全：Flag 路径、权限和属主、谁在什么时候读它、平台覆盖命令、程序读的不是 `flag.path` 时的接法。
- **1.7 部署方式**是硬性清单：目录说明、构建命令、镜像 tar 导入、**带 `/start.sh` 的启动命令**、访问地址、平台写 Flag 命令、清理命令、改端口后的同步位置。八项都要有。
- **1.9 解题步骤**按真实顺序写，给可直接复制的命令和 payload、预期输出、截图位置，详细到别人照着能复现。
- **不写"常见失败现象"这一节**，排障记录不属于交付手册。
- 一句话说清一件事，不写"本题目旨在……"这类铺垫，不用加粗堆重点，不用 emoji。
- 迁移题、补全题要在 1.8 写明原资料缺口和补全边界。

### solve/solve.py

- 从环境变量 `HOST`、`PORT` 读目标地址；多端口题用 `PORT_<容器端口>`，例如 `PORT_8080`。可以再提供 `--host`、`--port` 参数，默认值取环境变量。
- 走原题的漏洞链拿 Flag，打印到 stdout，拿到时返回 0，拿不到返回非 0。
- 不在脚本里写死 Flag。verify.sh 每次写入随机测试 Flag，输出里出现它才算通过。
- 地址、偏移不要在脚本里写死。PIE 题每次运行的基址不同，格式化字符串的写入计数也依赖实际布局；要从程序里泄漏出来再算。
- 脚本要能从零跑通：起手就先连一次服务确认可达，再走漏洞链。
- 依赖只用 Python 标准库；必须用第三方库时在脚本开头注释写明 `pip install` 命令。
- 附件题也照这个写：从 `附件/` 里的文件解出 Flag，如果题目需要远程服务才能解，就在手册里写清。

## 难度等价：不许降级兜底

这是硬要求。拿到只有源码、缺数据库快照、缺原二进制、缺依赖的旧题时，**不许因为本机跑不动、依赖拉不下来、链路太长，就换成一个更简单的能跑的变体交差**。

做法：

1. 先把原材料读透，写出这道题的难度构成：漏洞类型、影响面、链路有几步、要不要绕过防护（WAF、黑名单、权限校验）、需要什么前置知识。
2. 按这个难度做等价恢复。缺哪一块就补哪一块，补的方式要对得上源码里原有的调用方式：缺数据库就按源码里的查询反推建表和数据，缺二进制就从源码按原编译器、原 libc 重建。
3. **环境跑不动不是你改题的理由。** 本机是 Apple Silicon 跑不了 amd64 二进制、旧镜像拉不下来、模拟器里崩了，这些都是环境问题，要在 `challenge.yaml` 的 `provenance` 里如实记下来，把状态标成 `incomplete`，然后告诉用户卡在哪，问用户怎么办。
4. 确实无法等价恢复、必须换实现时，这是要用户拍板的事，停下来问，不要自己决定。用户同意后才能改，并且要在 `provenance` 里写清简化了什么、为什么、和原题的差距在哪。
5. 不许出现这些偷懒做法：把多步链路压成单接口直出 Flag；把需要绕过的防护删掉；把需要反推的数据结构换成自己编的一套；只用一条不依赖原材料的短路径就能拿 Flag。

`provenance` 字段（写进 `challenge.yaml`，见 [references/platform.md](references/platform.md)）：

```yaml
provenance:
  status: original_adapter        # original_adapter / independent_completion / incomplete / attachment_only
  original_material: [源码, install.sql, 题目说明.md]
  missing: [原数据库快照, 原二进制]
  preserved: [漏洞类型=前台 SQL 注入, 链路=3 步, 防护=原始黑名单]
  simplified: []                  # 有值必须写清简化了什么、为什么无法等价恢复
  env_limited: Apple ARM64 模拟下无法执行原始 rt_sigreturn
  verify: passed                  # passed / environment_failed / incomplete
```

`status` 的含义：

- `original_adapter`：原题材料完整，只补了平台合同（Flag 路径、start.sh、端口），漏洞逻辑原样保留。
- `independent_completion`：材料缺失，按原题的技术栈和难度独立补全，不是原题还原。手册里必须写明这一点。
- `incomplete`：材料缺失且没能等价恢复。**不许标成 passed**，在交付说明里写清缺什么、卡在哪。
- `attachment_only`：纯附件题，没有容器。

verify 通过只说明容器生命周期正常，**不等于**题目难度等价。不要把 `passed` 写成"原题已恢复"。

## 流程

复制这份清单，逐项完成：

```text
- [ ] 1. 确认题目类型、题目名称、容器题还是附件题、是不是 RDG
- [ ] 2. 读事实：启动方式、端口、运行时版本、Flag 路径、附件情况、资料缺口
- [ ] 3. 判断 provenance：原样恢复、独立补全，还是需要问用户
- [ ] 4. 整理 src/，附件放进 附件/
- [ ] 5. 写 Dockerfile 和 start.sh，带中文注释（附件题跳过）
- [ ] 6. 写 challenge.yaml（附件题跳过）
- [ ] 7. 写 solve/solve.py（RDG 题写 check/）
- [ ] 8. 写 README/ 手册，按 references/manual.md 的必填项逐条核对
- [ ] 9. 清理交付目录，只留白名单里的文件
- [ ] 10. 容器题：verify.sh 跑到 passed；附件题：solve.py 能解出 Flag
```

1. **读事实。** 已有的 Dockerfile、start.sh、challenge.yaml、依赖文件和手册里的部署说明先读完，能用的保留。端口、启动命令、运行时版本、Flag 路径缺了又推断不出来时，一次问完，不要猜。
2. **判断 provenance。** 材料完整就是 `original_adapter`；缺关键部分但能按原难度补全就是 `independent_completion`；补不出来或缺的东西影响漏洞链时停下来问用户，不要自己换简单实现。
3. **整理 src/。** 业务代码放进 `src/`，缺的部分补全到能跑。Pwn 题放发给选手的同一个二进制，不要在镜像里重新编译。
4. **写 Dockerfile 和 start.sh。** 照下面的范例写，各语言写法见 [references/dockerfiles.md](references/dockerfiles.md)。**必须带中文注释**，见"中文注释"一节。
5. **写 challenge.yaml。** 只填真实需要的字段，见下文。
6. **写 solve/solve.py。** 按上面的约定，走原题的漏洞链。RDG 题改写 `check/`，见"RDG 防守题"一节。
7. **写手册。** 逐条对照 [references/manual.md](references/manual.md) 里的必填项检查，特别是 1.2、1.5、1.7、1.9 四节。
8. **清理交付目录。** 交付目录里只允许白名单文件，把临时文件、验证脚本、报告、编辑器缓存全删掉，见"交付目录"一节。
9. **验证。** 运行本 Skill 目录下的 `scripts/verify.sh`：

   ```bash
   bash <本 Skill 目录>/scripts/verify.sh <题目目录>
   ```

   题目目录里有 `solve/solve.py` 时会自动运行它，输出里必须出现刚写入的随机测试 Flag。解题脚本不是 Python 时用 `--solve '<命令>'` 指定。RDG 题自动走 check 判定。

   `failed` 时按输出里的原因和日志修改，再跑一次，直到 `passed`。排查时加 `--keep` 保留容器，用 `docker logs` 看输出。`partial` 要在交付说明里写清哪一项没验证。

   报告写到系统临时目录（`--report` 的路径），**不要放进交付目录**。没跑 verify.sh 的题目不要说成已验证；没有 solve.py 时只能说明容器能跑，不能说明题目可解；`environment_failed` 只能说明本机跑不动，不能说明题目通过。

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

## RDG 防守题

RDG（防守加固）和普通题是两个赛制，交付物和验证方式都不一样。

**交付物差别：**

- 多一个 `check/` 目录，里面是判题脚本 `check.sh` + `check.py`，选手在平台上点"验证"时平台跑的就是它。
- 多一个 `/changeflag.sh`，旧平台通过 `FLAG` 环境变量传 Flag 时由它写入。
- 多一个 ttyd 服务，选手要通过浏览器进容器改代码。`start.sh` 里后台起 ttyd 并 `exec` 主服务。
- `challenge.yaml` 里 `category: RDG`、`check.enabled: true`、`check.path: check/check.sh`。

**check 脚本的契约**（照这个写，平台按这个接）：

- 调用方式 `./check.sh <IP> <PORT>`，也支持 `TARGET_IP`/`TARGET_PORT` 环境变量。
- 返回码 0 表示"这题是安全的/修好了"，非 0 表示"漏洞还在"。
- 输出里要有一行明确的判定，用 `ok: True` / `ok: False` 或 `RESULT: PASS` / `RESULT: FAIL`。
- 覆盖四类检测：服务可用性（页面、接口正常）、漏洞是否可复现（初始环境必须能打通）、通杀脚本检测（AoiAWD、watchbird、drop_wiki 这类）、账号可用性（后台 `admin/admin` 还能登录）。
- 脚本依赖只写进 `check/requirements.txt`，用 `requests` 这类通用库。

**不是所有 RDG 题都需要动态 Flag。** 两种形态都要支持：

- **有 Flag 合同**：平台写 `/flag`，check 通过"能不能拿到 Flag"判断漏洞是否被修复。
- **没有 Flag 合同**：敏感目标就是题目自己配置里的固定内容（虚拟主机配置、固定口令、错误页跳转），check 直接验证那个目标还能不能被读到，不涉及 `/flag`。这种题 `challenge.yaml` 里可以不写 `flag:` 块或注明 Flag 不是判据。

**verify.sh 的 RDG 模式**：带 `check/` 的题目自动走 RDG 判定，先跑一遍 check 确认初始环境返回"有漏洞"，再跑构建、启动、端口、ttyd 检查。没有 `check/` 时按普通题走。跑法不变：

```bash
bash <本 Skill 目录>/scripts/verify.sh <题目目录>
```

**手册**：RDG 题的 1.5 要说明 Flag 是动态写入还是固定值设计的一部分；1.9 改成"初始漏洞验证 + 修复方法 + 加固后自检"，把 check 在加固前后的预期输出都贴出来。详见 [references/manual.md](references/manual.md)。

完整的 RDG 交付形态和字段见 [references/special.md](references/special.md)。

## 中文注释

交付的代码**必须有中文注释**，这是硬性要求，扫一眼 Dockerfile 没有注释就是没做完。

- **Dockerfile**：每一段 `RUN`、`COPY`、每个扩展安装、每个版本锁定、每条平台约束都要说明为什么。典型写法：

  ```dockerfile
  FROM php:8.1-fpm-alpine

  # 解法依赖 pcntl_fork + pcntl_exec 绕过 disable_functions，官方镜像默认没编译 pcntl。
  RUN set -eux; \
      apk add --no-cache nginx bash; \
      docker-php-ext-install pcntl

  # nginx 与 php-fpm 共用容器，配置放在 /etc/nginx 而不是项目目录。
  COPY nginx/nginx.conf /etc/nginx/nginx.conf

  WORKDIR /var/www/html
  COPY src/ /var/www/html/

  # 平台用 /start.sh 覆盖 CMD 启动，权限 555 保证选手改不了启动逻辑。
  COPY start.sh /start.sh
  # 占位 Flag，平台启动后会用真实值覆盖；444 防止选手直接改。
  COPY flag /flag
  RUN chmod 555 /start.sh && chmod 444 /flag

  EXPOSE 80
  CMD ["/start.sh"]
  ```

- **业务源码**：漏洞点在哪、关键分支为什么这样写。
- **start.sh**：启动顺序、等待条件、为什么这样保活或转发信号。
- **check/ 脚本**：每个检测点查的是什么、判定标准是什么。

注释只写不明显的内容。以下注释不要写：

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
provenance:
  status: original_adapter         # original_adapter / independent_completion / incomplete / attachment_only
  original_material: [源码, install.sql]
  missing: []
  preserved: [漏洞类型=文件上传 TOCTOU, 链路=3 步]
  simplified: []
  env_limited: ""
  verify: passed
```

`provenance` 是必填的。只补了平台合同就写 `original_adapter`；材料缺失后独立重建写 `independent_completion` 并在手册里写明不是原题还原；没能等价恢复写 `incomplete` 并停下问用户。完整字段见 [references/platform.md](references/platform.md)。

## 特殊题型

输入确实是下面这些形态，或用户明确要求时，读 [references/special.md](references/special.md)：

- 多服务、docker-compose、Vulhub 类环境
- Bundle、BaseUnit 组合环境
- Scenario 多阶段编排
- RDG、AWD、AWDP、SecOps
- Linux kernel、QEMU guest
- 依赖 `changeflag.sh` 的旧平台题目

常规单服务题不读这个文件，也不要把多服务题压成单服务。
