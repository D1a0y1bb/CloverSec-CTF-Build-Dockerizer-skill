# CloverSec CTF Build Dockerizer

把一个 CTF 题目想法或半成品源码，整理成可以直接上平台的干净交付目录。

---

## 这是什么

一个给 Claude / Codex 用的 Skill。你把题目设计、一段参考代码或者现有的乱目录丢给它，它产出一个你自己一眼能看懂的题目目录：

```
<题目名>/
├── src/          # 题目源码
├── Dockerfile
├── start.sh
├── challenge.yaml
├── .dockerignore
└── flag          # 仅启动前需要占位时保留
```

然后用 `scripts/verify.sh` 真实构建、起容器、写测试 flag、打一遍服务入口，确认能跑。

覆盖范围：Web / Pwn / AI / Misc 等常规 Docker 题，以及多服务、Bundle、Scenario、RDG/AWD、Linux-QEMU 等特殊形态（按需查 references）。

---

## 开始使用

在 Claude Code / Codex 的对话里说：

> 用 `$cloversec-ctf-build-dockerizer` 帮我把这道题做出来……

然后把题目设计、参考代码或现有目录路径告诉它就行。

本地验证已有目录：

```bash
bash scripts/verify.sh <题目目录>
```

---

## 设计原则

**模型写代码，脚本做验证。** 题目的业务逻辑、目录结构、中文注释——这些由模型来完成，而不是靠模板管线压制。`scripts/verify.sh` 只负责最后的真实构建和运行验证。

**只产出运行需要的文件。** 题解、解题脚本、部署手册、历史说明不进交付目录。

**注释讲"为什么"，不复读代码。** 漏洞点在哪、这个配置为什么这么写、等待条件是什么——这些值得写。"切换到 /app 目录"这种不值得写。

---

## 文件说明

```
SKILL.md                  # Skill 入口，AI 工具加载这个
references/
  platform.md             # 平台合同、Flag 路径约定、challenge.yaml 字段
  dockerfiles.md          # 各栈（Python/Node/PHP/Java/Pwn）的 Dockerfile 和 start.sh 范例
  special.md              # 多服务、Bundle、QEMU、旧平台 helper 等特殊情况
scripts/
  verify.sh               # 本地验证脚本
legacy/                   # 历史渲染器、模板、示例（保留但不参与默认构建）
```

---

## Flag 合同

平台起容器后直接往 `challenge.yaml` 里 `flag.path` 指定的文件写动态 flag。你只需要写对路径：

| 题型 | 常见路径 |
|---|---|
| Web（大多数） | `/flag` |
| Pwn | `/home/ctf/flag` |
| PHP 嵌入文件 | `/var/www/html/flag.php` |
| 数据库 | 手册里记 SQL 命令 |

程序**每次请求时**读这个文件，不要在启动时缓存——否则平台改了 flag 程序还返回旧值。

---

## 版本

版本历史见 [CHANGELOG.md](CHANGELOG.md)。
