<p align="center">
  <img src=".github/assets/banner.svg" alt="CloverSec-CTF-Build-Dockerizer" width="860" />
</p>

<p align="center">
  <a href="https://github.com/D1a0y1bb/CloverSec-CTF-Build-Dockerizer-skill/releases/latest"><img src="https://img.shields.io/github/v/release/D1a0y1bb/CloverSec-CTF-Build-Dockerizer-skill?style=for-the-badge&color=2563eb&label=release" alt="Release" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/github/license/D1a0y1bb/CloverSec-CTF-Build-Dockerizer-skill?style=for-the-badge&color=16a34a" alt="License" /></a>
  <img src="https://img.shields.io/badge/Claude_Code_%C2%B7_Codex-skill-f59e0b?style=for-the-badge" alt="Claude Code · Codex" />
</p>

<p align="center">
  <strong>简体中文</strong> · <a href="README.en.md">English</a>
</p>

<p align="center">
  <a href="#安装">安装</a> ·
  <a href="#使用">使用</a> ·
  <a href="#交付目录">交付目录</a> ·
  <a href="#本地验证">本地验证</a> ·
  <a href="#flag-约定">Flag 约定</a> ·
  <a href="#仓库结构">仓库结构</a>
</p>

---

四叶草安全创研中心出题用的 Agent Skill。把题目源码、一段题目设计或者一个旧题目录交给 Claude Code / Codex，整理出能直接导入竞赛平台的容器题目录，再在本机 build、起容器、写 Flag、探端口验证一遍。

- 源码、`Dockerfile`、`start.sh` 由模型参照 Skill 里的范例编写，带中文注释，讲清漏洞点和不明显的配置。
- 内置 Python、Node、PHP、PHP-FPM + nginx、Java、静态页面、C/Pwn 七种写法范例。
- `verify.sh` 在本机真实构建运行，结果分 `passed` / `partial` / `failed`。
- 需要长期存档的题，按参考文档锁定镜像 digest、apt 源和依赖版本，上游更新后照样能 build。
- 多服务、Bundle、Scenario、RDG/AWD、Linux-QEMU 有单独的参考文档，常规题不加载。

## 安装

```bash
npx skills add D1a0y1bb/CloverSec-CTF-Build-Dockerizer-skill -g -a claude-code -a codex
```

`-g` 装到用户目录 `~/.agents/skills/`，Claude Code 通过软链接读取；去掉 `-g` 装进当前项目。`-a` 指定装给哪些 Agent，可以写多个。

本机需要 Docker，验证脚本用到 `curl` 和 `nc`。

## 使用

在对话里点名 Skill，再给材料。Claude Code 用 `/cloversec-ctf-build-dockerizer`，Codex 用 `$cloversec-ctf-build-dockerizer`：

```text
/cloversec-ctf-build-dockerizer 把 ./ssti-notes 做成平台题目。
Flask 写的 SSTI，flag 放 /flag，端口 5000。
```

材料可以是题目设计、只有源码的目录，或者带旧 Dockerfile 的历史题目。端口、启动命令、运行时版本、Flag 路径这类会卡住构建的信息如果缺了，它会一次问完，不会自己猜。

## 交付目录

```text
ssti-notes/
├── src/
│   ├── app.py
│   └── requirements.txt
├── Dockerfile
├── start.sh            # 平台入口，前台 exec 真实服务
├── challenge.yaml      # 端口、Flag 路径等平台字段
├── .dockerignore
└── flag                # 占位 Flag，平台启动后覆盖
```

目录里只放运行需要的文件，题解、exp、抓包和出题手册另外保存。

## 本地验证

```bash
bash ~/.agents/skills/cloversec-ctf-build-dockerizer/scripts/verify.sh ./ssti-notes
```

脚本会 build 镜像，用 `/start.sh` 起容器，往 `flag.path` 写一个测试 Flag 再读回来，然后探测端口。跑完删除容器和镜像，加 `--keep` 保留。

```text
== 构建镜像 ctf-verify-ssti-notes:test
== 启动容器
   容器运行中
== 写测试 Flag 到 /flag
   Flag 回读一致
== 探测端口 localhost:64108
   HTTP 200

== 结果: passed
```

| 结果 | 含义 |
|---|---|
| `passed` | 构建、启动、Flag 回读、端口探测全部通过 |
| `partial` | 容器起来了，但有检查项没过，输出里会逐条列出 |
| `failed` | 构建失败，或者容器没跑起来 |

端口和 Flag 路径默认从 `challenge.yaml` 读取，也可以用 `--port`、`--flag-path` 指定。

## Flag 约定

平台起容器后，直接把本场的动态 Flag 写进 `challenge.yaml` 中 `flag.path` 指向的文件。这个路径必须是程序实际读取的那个：

| 题型 | 常用路径 |
|---|---|
| Web / AI / Misc | `/flag` |
| Pwn | `/home/ctf/flag` |
| PHP 嵌入 Flag | `/var/www/html/flag.php` |
| 数据库 | 在手册里写清更新 Flag 的 SQL |

程序要在每次请求时读取 Flag 文件。启动时读一次存进变量（Python 模块级变量、Java `static` 块），平台换了 Flag 也不会生效。

## 仓库结构

```text
src/CloverSec-CTF-Build-Dockerizer/
├── SKILL.md              # 入口：交付目录、写法范例、注释要求、Flag 约定
├── references/
│   ├── platform.md       # 平台启动方式、Flag 路径、challenge.yaml 字段
│   ├── dockerfiles.md    # 各语言 Dockerfile / start.sh 范例、镜像版本固定
│   └── special.md        # 多服务、Bundle、Scenario、RDG/AWD、Linux-QEMU
└── scripts/
    └── verify.sh         # 本地构建与运行验证
```

版本记录见 [CHANGELOG.md](CHANGELOG.md)。

## License

[MIT](LICENSE)
