#!/usr/bin/env bash
# verify.sh —— 按平台的方式跑一遍题目：构建、/start.sh 启动、写入测试 Flag、探测端口，可选跑解题脚本。
#
# 用法：
#   bash verify.sh <题目目录> [选项]
#
# 选项：
#   --port N          要探测的容器端口，可重复；默认读 challenge.yaml 的 expose_ports，再退到 Dockerfile 的 EXPOSE
#   --flag-path P     平台写入 Flag 的路径；默认读 challenge.yaml 的 flag.path，再退到 /flag
#   --solve CMD       写入测试 Flag 后执行的解题命令；不给时题目目录有 solve/solve.py 就运行它
#                     环境变量 HOST、PORT 指向第一个端口，PORT_<容器端口> 指向各个端口，输出里必须出现测试 Flag
#   --platform P      构建和运行的平台，默认 linux/amd64（与比赛平台一致）
#   --timeout N       等待服务开始监听的秒数，默认 60
#   --keep            结束后保留容器和镜像，便于进去排查
#   --report PATH     把构建日志、端口结果和阶段结论写成 JSON 报告
#
# 退出码：0 passed / 1 failed / 2 参数错误 / 3 partial / 4 environment_failed
#   每一阶段都单独给结论，最后汇总成一行：
#     build: passed  startup: passed  port: passed  flag_write: passed  solve: passed
#   failed              明确违反平台合同，或解题拿不到 Flag
#   partial             能跑，但有检查无法完成（没声明端口、自定义 ENTRYPOINT 等）
#   environment_failed  本机环境跑不动（amd64 模拟下被调试的二进制崩溃等），题目本身没错
set -uo pipefail

usage() { sed -n '2,25p' "$0" | sed 's/^# \{0,1\}//'; exit 2; }

PROJECT=""; PORTS=(); FLAGPATH=""; SOLVE=""; PLATFORM="linux/amd64"; KEEP=0; REPORT=""
# Java、php-fpm、MySQL 冷启动常见 10~40 秒，amd64 模拟运行还会更慢，60 秒留出余量。
START_TIMEOUT=60
# 解题脚本一般几秒结束；竞态类题目要多跑几轮，给到 120 秒。
SOLVE_TIMEOUT=120

while [ $# -gt 0 ]; do
  case "$1" in
    --port) PORTS+=("${2:?--port 需要参数}"); shift 2;;
    --flag-path) FLAGPATH="${2:?--flag-path 需要参数}"; shift 2;;
    --solve) SOLVE="${2:?--solve 需要参数}"; shift 2;;
    --platform) PLATFORM="${2:?--platform 需要参数}"; shift 2;;
    --timeout) START_TIMEOUT="${2:?--timeout 需要参数}"; shift 2;;
    --keep) KEEP=1; shift;;
    --report) REPORT="${2:?--report 需要参数}"; shift 2;;
    -h|--help) usage;;
    -*) echo "未知参数: $1"; usage;;
    *) [ -z "$PROJECT" ] && PROJECT="$1" || { echo "多余参数: $1"; usage; }; shift;;
  esac
done
[ -n "$PROJECT" ] || usage
command -v docker >/dev/null || { echo "failed: 找不到 docker"; exit 1; }
command -v curl >/dev/null || { echo "failed: 找不到 curl"; exit 1; }
PROJECT=$(cd "$PROJECT" 2>/dev/null && pwd) || { echo "failed: 目录不存在"; exit 2; }
cd "$PROJECT" || exit 2

STATUS=passed; NOTES=(); HINTS=(); STAGE=()
fail()    { STATUS=failed; NOTES+=("$1"); }
partial() { [ "$STATUS" = passed ] && STATUS=partial; NOTES+=("$1"); }
envfail() { STATUS=environment_failed; NOTES+=("$1"); }
hint()    { HINTS+=("$1"); }
stage() { # 同一阶段重复设置时只保留最后一次结论
  local i
  for i in "${!STAGE[@]}"; do
    [ "${STAGE[$i]%%:*}" = "$1" ] && { STAGE[$i]="$1: $2"; return; }
  done
  STAGE+=("$1: $2")
}

write_report() {
  [ -n "$REPORT" ] || return 0
  {
    printf '{\n  "project": "%s",\n  "status": "%s",\n  "platform": "%s",\n  "host_emulated": %s,\n  "stages": {' "$PROJECT" "$STATUS" "$PLATFORM" "${HOST_IS_EMULATED:-0}"
    first=1
    for e in "${STAGE[@]+"${STAGE[@]}"}"; do
      k=${e%%:*}; v=${e#*: }
      [ "$first" = 1 ] || printf ','
      printf '\n    "%s": "%s"' "$k" "$v"; first=0
    done
    printf '\n  },\n  "notes": ['
    first=1
    for n in "${NOTES[@]+"${NOTES[@]}"}"; do
      [ "$first" = 1 ] || printf ','
      printf '\n    "%s"' "$(printf '%s' "$n" | sed 's/"/\\"/g')"; first=0
    done
    printf '\n  ]\n}\n'
  } > "$REPORT"
  echo "   报告: ${REPORT}"
}

finish() {
  write_report
  echo
  [ ${#STAGE[@]} -gt 0 ] && echo "== 阶段: ${STAGE[*]}"
  echo "== 结果: $STATUS"
  for n in "${NOTES[@]+"${NOTES[@]}"}"; do echo "   - $n"; done
  for h in "${HINTS[@]+"${HINTS[@]}"}"; do echo "   提示: $h"; done
  case "$STATUS" in
    passed) exit 0;;
    partial) exit 3;;
    environment_failed) exit 4;;
    *) exit 1;;
  esac
}

BUILDLOG=$(mktemp); SOLVELOG=$(mktemp)
trap cleanup EXIT

# ---------- 构建前的静态检查：这些问题会让容器起不来，提前说清楚比翻日志快
if [ ! -f Dockerfile ]; then
  # 附件题：没有容器，只检查交付结构和解题脚本。
  if [ -f "${PROJECT}/solve/solve.py" ] || [ -d "${PROJECT}/附件" ]; then
    echo "== 附件题（没有 Dockerfile，跳过容器验证）"
    shopt -s nullglob dotglob
    ATT=("${PROJECT}/附件"/*)
    if [ ${#ATT[@]} -eq 0 ]; then
      partial "附件/ 是空的，确认选手该拿到哪些文件"
    else
      echo "   附件 ${#ATT[@]} 个"
      for a in "${ATT[@]}"; do echo "   - $(basename "$a")"; done
      stage attachments passed
    fi
    ls "${PROJECT}/README"/*.md >/dev/null 2>&1 || hint "README/ 下没有手册，手册是交付的一部分"
    # 附件题也要用解题脚本确认题目真的能解，否则只证明目录结构像附件题。
    if [ -f "${PROJECT}/solve/solve.py" ]; then
      echo "== 运行解题脚本"
      ( cd "$PROJECT" && python3 solve/solve.py ) >"$SOLVELOG" 2>&1
      if [ $? -ne 0 ]; then
        tail -15 "$SOLVELOG" | sed 's/^/   | /'
        stage solve failed; fail "solve/solve.py 返回非 0"
      elif grep -qE '[A-Za-z0-9_]+\{[^}]{4,}\}' "$SOLVELOG"; then
        echo "   解出 $(grep -oE '[A-Za-z0-9_]+\{[^}]{4,}\}' "$SOLVELOG" | head -1)"
        stage solve passed
      else
        tail -15 "$SOLVELOG" | sed 's/^/   | /'
        stage solve failed; fail "solve/solve.py 的输出里没有 Flag"
      fi
    else
      stage solve missing
      hint "没有 solve/solve.py，只整理了附件，没有验证题目可解"
    fi
    finish
  fi
  fail "没有 Dockerfile，也不是附件题（没有 附件/ 和 solve/solve.py）"; finish
fi
if [ -f start.sh ]; then
  if grep -q $'\r' start.sh; then
    fail "start.sh 是 CRLF 换行，容器里会报 bad interpreter，转成 LF 后再验证"; finish
  fi
  head -n1 start.sh | grep -q '^#!' || { fail "start.sh 第一行没有 #!，平台执行 /start.sh 会报 exec format error"; finish; }
fi
# COPY . 会把 solve/、README/、附件/、镜像/ 一起打进镜像，路径也会变，直接拦下来。
if grep -qiE '^[[:space:]]*(COPY|ADD)[[:space:]]+(--[^[:space:]]+[[:space:]]+)*\./?[[:space:]]' Dockerfile; then
  fail "Dockerfile 用了 COPY . ，会把 solve/、README/、附件/ 打进镜像，并且改变目录结构，改成 COPY 具体路径"; finish
fi
[ -n "$SOLVE" ] || { [ -f solve/solve.py ] && SOLVE="python3 solve/solve.py"; }

YAML=challenge.yaml
if [ ${#PORTS[@]} -eq 0 ] && [ -f "$YAML" ]; then
  # 兼容 expose_ports: ["80", "22"] 和逐行 - "80" 两种写法。
  for p in $(awk '
    /^[[:space:]]*expose_ports:/ { s=$0; sub(/.*expose_ports:/, "", s); if (s ~ /\[/) { print s; exit } blk=1; next }
    blk { if ($0 ~ /^[[:space:]]*-/) print; else if ($0 !~ /^[[:space:]]*$/) exit }
  ' "$YAML" | grep -oE '[0-9]+'); do PORTS+=("$p"); done
fi
if [ ${#PORTS[@]} -eq 0 ]; then
  for p in $(grep -iE '^[[:space:]]*EXPOSE[[:space:]]' Dockerfile | grep -oE '[0-9]+'); do PORTS+=("$p"); done
fi
if [ -z "$FLAGPATH" ] && [ -f "$YAML" ]; then
  # 只在 flag: 块里找 path，避免拿到 verification 等其他块的 path。
  FLAGPATH=$(awk '
    /^[[:space:]]*flag:[[:space:]]*$/ { inb=1; ind=match($0, /[^ ]/); next }
    inb && $0 !~ /^[[:space:]]*$/ {
      if (match($0, /[^ ]/) <= ind) exit
      if ($0 ~ /^[[:space:]]*path:/) { sub(/^[[:space:]]*path:[[:space:]]*/, ""); sub(/[[:space:]]+#.*/, ""); gsub(/["'\'']/, ""); print; exit }
    }' "$YAML")
fi
[ -n "$FLAGPATH" ] || FLAGPATH=/flag

# HTTP 探测路径：根路径返回 403/404 不代表服务有问题，题目可以用
# verification.solve_probe.path 指定真实入口。
PROBE_PATH=/
if [ -f "$YAML" ]; then
  CASE_PATH=$(awk '
    /^[[:space:]]*solve_probe:[[:space:]]*$/ { inb=1; next }
    inb && /^[[:space:]]*[a-zA-Z_]+:[[:space:]]*$/ { inb=0 }
    inb && /^[[:space:]]*path:[[:space:]]*[^[:space:]]/ {
      sub(/^[[:space:]]*path:[[:space:]]*/, ""); sub(/[[:space:]]+#.*/, "")
      gsub(/["'"'"']/, ""); print; exit
    }' "$YAML")
  [ -n "$CASE_PATH" ] && PROBE_PATH="$CASE_PATH"
fi
case "$PROBE_PATH" in /*) ;; *) PROBE_PATH="/$PROBE_PATH";; esac

# 镜像名只允许小写字母数字，中文目录名或 "." 直接拿来当 tag 会让 docker build 报错。
SLUG=$(basename "$PROJECT" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+//; s/-+$//')
SUFFIX=$(printf '%s' "$PROJECT" | cksum | cut -d' ' -f1)
# 本机架构与目标架构不一致时，走的是模拟运行，解题阶段要区分题目失败和环境失败。
case "$PLATFORM" in
  *arm64*|*aarch64*) PLATFORM_ARCH=arm64;;
  *) PLATFORM_ARCH=amd64;;
esac
case "$(docker info --format '{{.Architecture}}' 2>/dev/null)" in
  x86_64|amd64) HOST_ARCH=amd64;;
  aarch64|arm64) HOST_ARCH=arm64;;
  *) HOST_ARCH="";;
esac
if [ -n "$HOST_ARCH" ] && [ "$PLATFORM_ARCH" != "$HOST_ARCH" ]; then HOST_IS_EMULATED=1; else HOST_IS_EMULATED=0; fi

IMAGE="ctf-verify-${SLUG:-challenge}-${SUFFIX}:test"
CONTAINER="ctf-verify-$$"

cleanup() {
  rm -f "$BUILDLOG" "$SOLVELOG"
  if [ "$KEEP" = 1 ]; then
    echo "[keep] 容器 ${CONTAINER}，镜像 ${IMAGE}"
    echo "   排查完删除: docker rm -f ${CONTAINER} && docker rmi ${IMAGE}"
    return
  fi
  docker rm -f "$CONTAINER" >/dev/null 2>&1
  docker rmi "$IMAGE" >/dev/null 2>&1
}

show_logs() { echo "   ---- docker logs 最后 30 行"; docker logs "$CONTAINER" 2>&1 | tail -30 | sed 's/^/   | /'; }

# ---------- 构建
echo "== 构建镜像 ($PLATFORM)"
T0=$(date +%s)
if ! docker build --platform "$PLATFORM" -t "$IMAGE" . >"$BUILDLOG" 2>&1; then
  echo "   ---- 构建日志最后 40 行"; tail -40 "$BUILDLOG" | sed 's/^/   | /'
  stage build failed; fail "docker build 失败"; finish
fi
echo "   完成，用时 $(( $(date +%s) - T0 )) 秒"
stage build passed

# 官方 php/nginx/node 镜像的 docker-*entrypoint 会把参数原样 exec，不影响 /start.sh；其他 ENTRYPOINT 会吞掉它。
ENTRY=$(docker image inspect -f '{{json .Config.Entrypoint}}' "$IMAGE" 2>/dev/null)
case "$ENTRY" in null|\[\]|""|*docker-*entrypoint*) ;; *) partial "镜像设置了 ENTRYPOINT ${ENTRY}，平台传入的 /start.sh 会变成它的参数，确认它最后会执行 /start.sh";; esac

# ---------- 启动：和平台一样以 /start.sh 为命令；端口只绑本机，漏洞服务不暴露到局域网
echo "== 启动容器"
RUN_ARGS=(-d --name "$CONTAINER" --platform "$PLATFORM")
for p in "${PORTS[@]+"${PORTS[@]}"}"; do RUN_ARGS+=(-p "127.0.0.1::$p"); done
if ! docker run "${RUN_ARGS[@]}" "$IMAGE" /start.sh >/dev/null 2>"$BUILDLOG"; then
  sed 's/^/   | /' "$BUILDLOG"; stage startup failed; fail "容器启动失败"; finish
fi
stage startup passed

# 读容器内的 /proc/net/tcp 判断真实监听。Docker Desktop 的端口转发在服务没起来时也会接受连接，
# 只从宿主机探测会误判成"已连通"。
listen_state() { # 输出 any / loopback / none
  local want=$1 table addr port state=none
  table=$(docker exec "$CONTAINER" sh -c 'cat /proc/net/tcp /proc/net/tcp6 2>/dev/null' 2>/dev/null) || { echo unknown; return; }
  [ -n "$table" ] || { echo unknown; return; }
  for addr in $(printf '%s\n' "$table" | awk '$4=="0A" {print $2}'); do
    port=$(( 16#${addr##*:} ))
    [ "$port" = "$want" ] || continue
    case "${addr%%:*}" in
      0100007F|00000000000000000000000001000000) [ "$state" = none ] && state=loopback;;
      *) state=any;;
    esac
  done
  echo "$state"
}

running() { [ "$(docker inspect -f '{{.State.Running}}' "$CONTAINER" 2>/dev/null)" = true ]; }

if [ ${#PORTS[@]} -gt 0 ]; then
  echo "   等待端口 ${PORTS[*]} 开始监听（最多 ${START_TIMEOUT} 秒）"
  T0=$(date +%s)
  while :; do
    running || break
    ALL=1
    for p in "${PORTS[@]}"; do [ "$(listen_state "$p")" = any ] || ALL=0; done
    [ "$ALL" = 1 ] && break
    [ $(( $(date +%s) - T0 )) -ge "$START_TIMEOUT" ] && break
    sleep 1
  done
else
  sleep 3
fi
if ! running; then
  show_logs; stage startup failed; fail "容器已退出，start.sh 需要在前台运行真实服务"; finish
fi
echo "   容器运行中"

PID1=$(docker exec "$CONTAINER" sh -c 'tr "\0" " " </proc/1/cmdline' 2>/dev/null)
case "$PID1" in *start.sh*) hint "PID 1 是 start.sh（${PID1}），确认主服务退出时 start.sh 也会退出，否则平台发现不了题目挂掉";; esac

# ---------- 写入测试 Flag：命令和平台一致，以 root 用 sh 重定向写入
# 以 root 重定向总能写成功，所以"写不进去"不能当判据；先看题目有没有 Flag 合同。
NO_FLAG_CONTRACT=0
if [ ! -f "$YAML" ] || ! grep -qE '^[[:space:]]*flag:' "$YAML"; then
  NO_FLAG_CONTRACT=1
fi
if [ ! -f flag ] && ! grep -qiE '^[[:space:]]*(COPY|ADD)[^\n]*flag([[:space:]]|$)' Dockerfile; then
  NO_FLAG_CONTRACT=1
fi

echo "== 写入测试 Flag 到 ${FLAGPATH}"
TESTFLAG="flag{verify_$(od -An -N6 -tx1 /dev/urandom | tr -d ' \n')}"
if docker exec -u 0 "$CONTAINER" sh -c 'printf "%s\n" "$1" > "$2"' sh "$TESTFLAG" "$FLAGPATH" 2>/dev/null; then
  BACK=$(docker exec -u 0 "$CONTAINER" cat "$FLAGPATH" 2>/dev/null | tr -d '\r\n')
  MODE=$(docker exec -u 0 "$CONTAINER" stat -c '%a %U:%G' "$FLAGPATH" 2>/dev/null)
  if [ "$BACK" != "$TESTFLAG" ]; then
    stage flag_write failed; fail "Flag 写入后回读不一致"
  elif [ "$NO_FLAG_CONTRACT" = 1 ]; then
    stage flag_write partial
    partial "题目没有 Flag 合同：challenge.yaml 没有 flag.path，镜像里也没有占位 Flag 文件。平台能写进 ${FLAGPATH}，但程序未必读它，先补上读取逻辑"
  else
    echo "   回读一致（${MODE}）"; stage flag_write passed
  fi
else
  stage flag_write failed
  fail "平台无法写入 ${FLAGPATH}（镜像里没有 sh，或目录不存在）"
fi

# ---------- 端口探测
FIRST_HOSTPORT=""; SOLVE_ENV=(); PORTS_OK=1
for p in "${PORTS[@]+"${PORTS[@]}"}"; do
  HP=$(docker port "$CONTAINER" "$p/tcp" 2>/dev/null | head -1 | sed -E 's/.*:([0-9]+)$/\1/')
  [ -n "$FIRST_HOSTPORT" ] || FIRST_HOSTPORT=$HP
  SOLVE_ENV+=("PORT_$p=$HP")
  echo "== 探测端口 ${p}（本机 127.0.0.1:${HP}）"
  case "$(listen_state "$p")" in
    loopback) PORTS_OK=0; fail "端口 $p 只监听 127.0.0.1，平台映射后访问不到，改成 0.0.0.0"; continue;;
    none) PORTS_OK=0; fail "端口 $p 在 ${START_TIMEOUT} 秒内没有开始监听"; show_logs; continue;;
    unknown) hint "读不到容器内的监听表，端口 $p 只能从宿主机探测，TCP 结果可能不准";;
  esac
  CODE=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "http://127.0.0.1:${HP}${PROBE_PATH}" 2>/dev/null)
  [ "$PROBE_PATH" = / ] || echo "   探测路径 ${PROBE_PATH}"
  if [ -n "$CODE" ] && [ "$CODE" != 000 ]; then
    echo "   HTTP $CODE"
    [ "$CODE" -ge 500 ] && partial "端口 $p 返回 HTTP ${CODE}，服务可能有报错"
  else
    BANNER=$(curl -s --max-time 3 "telnet://127.0.0.1:$HP" </dev/null 2>/dev/null | LC_ALL=C tr -cd '[:print:]\n' | grep -v '^$' | head -2)
    if [ -n "$BANNER" ]; then
      printf '%s\n' "$BANNER" | sed 's/^/   TCP 输出: /'
    else
      echo "   TCP 已监听，连接后没有输出"
    fi
  fi
done
[ ${#PORTS[@]} -gt 0 ] || partial "没有声明端口（challenge.yaml 的 expose_ports 或 Dockerfile 的 EXPOSE），跳过端口探测"
[ "$PORTS_OK" = 1 ] && [ ${#PORTS[@]} -gt 0 ] && stage port passed

# ---------- 解题验证：拿到的是刚写入的测试 Flag，才说明程序按请求读取 Flag、没有缓存
if [ -z "$SOLVE" ]; then
  # 没有解题脚本时，"容器能跑"不等于"题目可解"，阶段回执里明确标出来。
  stage solve missing
  hint "没有 solve/solve.py，只验证了容器能跑，没有验证题目可解"
elif [ -n "$SOLVE" ]; then
  echo "== 运行解题命令: $SOLVE"
  case "$SOLVE" in
    *solve.py*) grep -qE 'HOST|PORT|argparse|--host|--port' solve/solve.py 2>/dev/null \
      || hint "solve/solve.py 里没有读 HOST/PORT 的代码，确认它能接受目标地址";;
  esac
  if [ -z "$FIRST_HOSTPORT" ]; then
    partial "没有可用端口，跳过解题命令"
  elif [[ "$SOLVE" == python3* ]] && ! command -v python3 >/dev/null; then
    partial "本机没有 python3，跳过解题命令"
  else
    # 多服务题常用每秒一次的循环把 /flag 同步进数据库，留 2 秒让它跟上。
    sleep 2
    ( cd "$PROJECT" && env HOST=127.0.0.1 PORT="$FIRST_HOSTPORT" "${SOLVE_ENV[@]+"${SOLVE_ENV[@]}"}" sh -c "$SOLVE" ) >"$SOLVELOG" 2>&1 &
    SPID=$!; T0=$(date +%s)
    while kill -0 "$SPID" 2>/dev/null && [ $(( $(date +%s) - T0 )) -lt "$SOLVE_TIMEOUT" ]; do sleep 1; done
    kill "$SPID" 2>/dev/null && hint "解题命令超过 ${SOLVE_TIMEOUT} 秒被终止"
    wait "$SPID" 2>/dev/null; SRC=$?
    if grep -qF "$TESTFLAG" "$SOLVELOG"; then
      echo "   拿到测试 Flag"
      stage solve passed
      [ "$SRC" = 0 ] || hint "解题命令拿到了 Flag 但退出码是 ${SRC}，约定成功时返回 0"
    else
      tail -15 "$SOLVELOG" | sed 's/^/   | /'
      # 本机模拟运行 amd64 时，被调试的二进制可能崩在模拟器里，这不是题目本身的问题。
      if [ "$HOST_IS_EMULATED" = 1 ] && grep -qE 'Segmentation fault|Bus error|Illegal instruction|core dumped|qemu:' "$SOLVELOG"; then
        stage solve environment_failed
        envfail "解题命令崩在本机模拟器里，题目本身可能没问题。换原生 amd64 机器重跑，或用 --platform linux/arm64 先确认镜像其余部分"
      else
        stage solve failed
        fail "解题命令的输出里没有测试 Flag ${TESTFLAG}（Flag 被缓存、路径不对，或解题脚本没打通）"
      fi
    fi
  fi
fi

finish
