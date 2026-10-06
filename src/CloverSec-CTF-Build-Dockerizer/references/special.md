# 特殊形态（按需查）

常规单服务题不要读这里。只有输入确实是下面某种形态、或用户明确要求时才用。
原则不变：模型照着范例写干净的、带中文注释的交付文件；能不多引入文件就不引入。

仓库 `legacy/` 保留了旧版的渲染器和各类模板（`render.py`、`render_scenario.py`、`render_bundle.py`、各栈模板等）。它们**不随 Skill 默认加载**，只在你确实要处理老环境、又不想手写时作为参考或兜底。优先手写干净版本；只有老环境复杂到手写不划算时才去翻 legacy。

---

## 多服务 / docker-compose / Vulhub-like

输入带 `docker-compose.yml`，或题目需要 web + db + redis 等多个容器。

- 能用单容器多进程解决的（如 nginx+php-fpm+一个 redis），优先单容器，`start.sh` 里按依赖顺序后台起、前台 exec 主服务。
- 真需要多容器编排的，保留/整理 `docker-compose.yml`，在 `challenge.yaml` 里标明这是 compose 题。各服务各自一个干净 Dockerfile。
- Flag 写入哪个服务、哪个路径，在手册里写清楚。

## Bundle / BaseUnit（组合环境）

把多个可复用基础单元（BaseUnit）组合成一道题。保留各单元边界清晰，别揉成一个大镜像。具体历史格式见 `legacy/`。

## Scenario（多阶段编排）

一道题分多个阶段/关卡，阶段间有状态流转。每个阶段源码独立成目录，编排关系写在配置里。历史 schema 见 `legacy/docs`。

## RDG / AWD / AWDP / SecOps

这些是对抗/运维类赛制，通常需要 check 脚本（判题/巡检）。写一个清晰的 check，说明判定逻辑。历史 check 模板见 `legacy/scripts/generate_check_stub.py`。

## Linux kernel / QEMU guest 题

内核 CVE/LPE 题，用 QEMU 起 guest。这类题的 Flag 在 guest 内部，host 层的 `changeflag.sh` 只写 host 文件、guest 看不到——Flag 要写进 rootfs 或由 guest 启动脚本读取。构建和手动验证流程见 `legacy/docs/linux_qemu_manual_validation.md`。

## 旧平台 helper（changeflag.sh）

有些老题/老平台约定由容器内 `/changeflag.sh` 来写 Flag，而不是平台直接写。只有这三种情况才需要它：
1. 迁移的老题本身就依赖 `/changeflag.sh`；
2. Linux-QEMU 需要 guest 注入；
3. 用户明确要求旧 helper 合同。

需要时的最小形态：

```bash
#!/bin/bash
set -euo pipefail
# 平台把新 flag 作为参数或 FLAG 环境变量传入，写到目标路径。
TARGET="${FLAG_PATH:-/flag}"
printf '%s\n' "${FLAG:-${1:-}}" > "$TARGET"
chmod 444 "$TARGET"
```

对应 Dockerfile 要 `COPY changeflag.sh /changeflag.sh` 且 `chmod 555`，并确保镜像里有 `/bin/bash`。常规 direct-write 题不需要这个文件。
