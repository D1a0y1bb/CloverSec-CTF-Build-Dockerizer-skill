# 特殊形态（按需查）

输入确实是下面这些形态，或用户明确要求时才读。写法要求和 SKILL.md 一样：带中文注释，只放运行需要的文件。

旧版渲染器和各类模板（`render.py`、`render_scenario.py`、`render_bundle.py`、各栈模板等）留在 [v3.0.1](https://github.com/D1a0y1bb/CloverSec-CTF-Pack/tree/v3.0.1/src/CloverSec-CTF-Build-Dockerizer) 标签里，不随 Skill 安装。优先手写干净版本；只有老环境复杂到手写不划算时，再去 v3.0.1 里翻对应文件参考。

---

## 多服务 / docker-compose / Vulhub-like

输入带 `docker-compose.yml`，或题目需要 web + db + redis 等多个容器。

nginx + php-fpm + redis + MySQL 这类能放进一个容器的，用单容器。start.sh 照下面的模板写，五段按题目删减：

```bash
#!/bin/bash
set -euo pipefail

# 后台服务的日志直接写到容器 stdout，docker logs 能看到全部进程的输出。
log() { echo "[start] $*"; }

# 1. 依赖服务：后台启动，日志带前缀并入 stdout。
log "starting mariadb"
mysqld_safe --user=mysql 2>&1 | sed -u 's/^/[mysql] /' &

# 2. 等依赖就绪：探测真实可用状态，超时直接失败，平台会看到容器退出。
for i in $(seq 1 60); do
    mysqladmin ping --silent 2>/dev/null && break
    [ "$i" = 60 ] && { log "mariadb not ready after 60s"; exit 1; }
    sleep 1
done

# 3. 初始化数据：脚本可重复执行，容器重启不会报错。
mysql < /app/init.sql

# 4. 主服务：后台启动以便下面同步 Flag；收到 TERM/INT 时转发给它，平台停止容器不用等超时。
log "starting app"
python3 /app/app.py &
MAIN_PID=$!
trap 'kill -TERM "$MAIN_PID" 2>/dev/null; mysqladmin shutdown 2>/dev/null' TERM INT

# 5. 平台在容器启动后才写 /flag，数据库里的 Flag 要跟着更新。
#    题目不需要同步时删掉这段，改成 exec 主服务。
sync_flag() {
    local value
    value=$(sed "s/\\\\/\\\\\\\\/g; s/'/''/g" /flag)
    mysql ctf -e "UPDATE flag SET value='${value}' WHERE id=1;"
    log "flag synced"
}
sync_flag
last=$(cksum < /flag)
while kill -0 "$MAIN_PID" 2>/dev/null; do
    now=$(cksum < /flag)
    [ "$now" != "$last" ] && { sync_flag; last=$now; }
    sleep 1
done

# 主服务退出时容器跟着退出，平台能发现题目挂了。
wait "$MAIN_PID"
```

- 第 5 段只在 Flag 存在数据库或配置文件里时需要；Flag 直接从 `/flag` 读的题删掉第 5 段，最后一行改成 `exec` 主服务。
- 后台服务不要把日志重定向到 `/tmp/*.log`，排查时 `docker logs` 看不到。
- 主服务是 `catalina.sh run`、`apache2-foreground` 这类前台命令时，第 4 段把它放后台即可。
- 排查时用 `verify.sh <题目目录> --keep` 保留容器，再 `docker logs -f <容器>` 看所有进程的输出。

必须多容器时保留 `docker-compose.yml`，每个服务一个 Dockerfile，手册写清 Flag 写进哪个服务的哪个路径。verify.sh 只验证单容器，compose 题用 `docker compose up` 手动验证。

## Bundle / BaseUnit（组合环境）

把多个可复用基础单元（BaseUnit）组合成一道题。保留各单元边界清晰，别揉成一个大镜像。历史格式见 v3.0.1 的 [`data/bundle_schema.md`](https://github.com/D1a0y1bb/CloverSec-CTF-Pack/blob/v3.0.1/src/CloverSec-CTF-Build-Dockerizer/data/bundle_schema.md)。

## Scenario（多阶段编排）

一道题分多个阶段/关卡，阶段间有状态流转。每个阶段源码独立成目录，编排关系写在配置里。历史 schema 见 v3.0.1 的 [`data/scenario_schema.md`](https://github.com/D1a0y1bb/CloverSec-CTF-Pack/blob/v3.0.1/src/CloverSec-CTF-Build-Dockerizer/data/scenario_schema.md)。

## RDG / AWD / AWDP / SecOps

这些是对抗/运维类赛制，通常需要 check 脚本（判题/巡检）。写一个清晰的 check，说明判定逻辑。历史 check 模板见 v3.0.1 的 [`scripts/generate_check_stub.py`](https://github.com/D1a0y1bb/CloverSec-CTF-Pack/blob/v3.0.1/src/CloverSec-CTF-Build-Dockerizer/scripts/generate_check_stub.py)。

## Linux kernel / QEMU guest 题

内核 CVE/LPE 题，用 QEMU 起 guest。这类题的 Flag 在 guest 内部，host 层的 `changeflag.sh` 只写 host 文件、guest 看不到——Flag 要写进 rootfs 或由 guest 启动脚本读取。构建和手动验证流程见 v3.0.1 的 [`docs/linux_qemu_manual_validation.md`](https://github.com/D1a0y1bb/CloverSec-CTF-Pack/blob/v3.0.1/src/CloverSec-CTF-Build-Dockerizer/docs/linux_qemu_manual_validation.md)。

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
