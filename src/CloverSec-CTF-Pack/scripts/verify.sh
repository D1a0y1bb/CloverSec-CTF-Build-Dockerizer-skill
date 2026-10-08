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
#   --check CMD       指定 RDG 判题命令；默认题目目录有 check/check.sh 就自动走 RDG 判定
#   --rdg             题目目录不在交付目录形态时，强制按 RDG 判定
#   --platform P      构建和运行的平台，默认 linux/amd64（与比赛平台一致）
#   --timeout N       等待服务开始监听的秒数，默认 60
#   --keep            结束后保留容器和镜像，便于进去排查
#   --report PATH     把构建日志、端口结果和阶段结论写成 JSON 报告。默认写到系统临时目录，
#                     路径只要落在交付目录里就拒绝执行，报告不属于交付物。
#
# 退出码：0 passed / 1 failed / 2 参数错误 / 3 partial / 4 environment_failed
#   每一阶段都单独给结论，最后汇总成一行：
#     普通题  build: passed  startup: passed  port: passed  flag_write: passed  solve: passed
#     RDG 题  build: passed  startup: passed  port: passed  flag_write: skipped  check_initial: ok: False
#   failed              明确违反平台合同，或解题拿不到 Flag，或 RDG 初始环境就是修好的
#   partial             能跑，但有检查无法完成（没声明端口、自定义 ENTRYPOINT 等），或交付目录有多余文件
#   environment_failed  本机环境跑不动（amd64 模拟下被调试的二进制崩溃等），题目本身没错
set -uo pipefail

usage() { sed -n '2,27p' "$0" | sed 's/^# \{0,1\}//'; exit 2; }

PROJECT=""; PORTS=(); FLAGPATH=""; SOLVE=""; CHECK=""; FORCE_RDG=0
PLATFORM="linux/amd64"; KEEP=0; REPORT=""
# Java、php-fpm、MySQL 冷启动常见 10~40 秒，amd64 模拟运行还会更慢，60 秒留出余量。
START_TIMEOUT=60
# 解题脚本一般几秒结束；竞态类题目要多跑几轮，给到 120 秒。
SOLVE_TIMEOUT=120

while [ $# -gt 0 ]; do
  case "$1" in
    --port) PORTS+=("${2:?--port 需要参数}"); shift 2;;
    --flag-path) FLAGPATH="${2:?--flag-path 需要参数}"; shift 2;;
    --solve) SOLVE="${2:?--solve 需要参数}"; shift 2;;
    --check) CHECK="${2:?--check 需要参数}"; shift 2;;
    --rdg) FORCE_RDG=1; shift;;
    --platform) PLATFORM="${2:?--platform 需要参数}"; shift 2;;
    --timeout) START_TIMEOUT="${2:?--timeout 需要参数}"; shift 2;;
    --keep) KEEP=1; shift;;
    --report) REPORT="${2:?--report 需要参数}"; shift 2;;
    -h|--help) usage;;
    -*) echo "未知参数: $1"; usage;;
    # 第一个非选项参数是题目目录，多出来的直接报错，避免悄悄忽略拼错的路径。
    *)
      if [ -z "$PROJECT" ]; then
        PROJECT="$1"
      else
        echo "多余参数: $1"; usage
      fi
      shift;;
  esac
done
[ -n "$PROJECT" ] || usage
command -v docker >/dev/null || { echo "failed: 找不到 docker"; exit 1; }
command -v curl >/dev/null || { echo "failed: 找不到 curl"; exit 1; }
PROJECT=$(cd "$PROJECT" 2>/dev/null && pwd) || { echo "failed: 目录不存在"; exit 2; }
cd "$PROJECT" || exit 2

# 报告是给跑验证的人看的，不是交付物。路径落在交付目录里直接拒绝，避免又把它交出去。
if [ -n "$REPORT" ]; then
  case "$(cd "$(dirname "$REPORT")" 2>/dev/null && pwd || echo "")" in
    "$PROJECT"|"$PROJECT"/*)
      echo "failed: --report 的路径在交付目录里（${REPORT}）。报告不属于交付物，写到系统临时目录，例如："
      echo "  --report \"\$(mktemp -d)/verify.json\""
      exit 2;;
  esac
fi

STATUS=passed; NOTES=(); HINTS=(); STAGE=()
fail()    { STATUS=failed; NOTES+=("$1"); }
partial() { [ "$STATUS" = passed ] && STATUS=partial; NOTES+=("$1"); }
envfail() { STATUS=environment_failed; NOTES+=("$1"); }
hint()    { HINTS+=("$1"); }
stage() { # 同一阶段重复设置时只保留最后一次结论
  local i
  for i in "${!STAGE[@]}"; do
    [ "${STAGE[$i]%%:*}" = "$1" ] && { STAGE[i]="$1: $2"; return; }
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

BUILDLOG=$(mktemp); SOLVELOG=$(mktemp); CHECKLOG=$(mktemp)
trap cleanup EXIT

# ---------- 交付目录白名单：用户拿到的是这个目录，多余文件就是垃圾
# 允许的顶层条目。RDG 题额外允许 check/、ttyd、changeflag.sh、php.ini 等题目真正运行需要的文件。
whitelisted() {
  case "$1" in
    src|Dockerfile|start.sh|challenge.yaml|flag|README|solve|附件|镜像) return 0;;
    check|changeflag.sh|ttyd|ttyd.conf|php.ini|docker-entrypoint.sh|xinetd.conf|ctf.xinetd) return 0;;
    last|lasted) return 0;;   # 出题人保留原始交付材料的目录，按惯例叫 last/lasted
    *) return 1;;
  esac
}

# 手册检查：文件名、章节骨架、事实字段、启动命令，以及 TODO 残留。
# 判断部分（1.2/1.4/1.8/1.9）本来就要留空给人工写，不检查内容——这个脚本查不出内容真假，
# 假装能查只会让人把"章节齐全"当成"手册写完"。
assert_handbook() {
  local expected base found=() todo
  base=$(basename "$PROJECT")
  shopt -s nullglob
  found=("${PROJECT}/README"/*.md)
  if [ ${#found[@]} -eq 0 ]; then
    stage handbook failed
    fail "README/ 下没有手册。手册是交付的一部分，文件名写成 README/${base}.md"
    return
  fi
  expected="${PROJECT}/README/${base}.md"
  if [ ! -f "$expected" ]; then
    stage handbook failed
    fail "手册文件名不对。必须是 README/${base}.md，现在是：$(printf '%s ' "${found[@]##*/}")"
    return
  fi

  # 章节骨架
  local missing=()
  for sec in '1.1' '1.2' '1.3' '1.4' '1.5' '1.6' '1.8' '1.9'; do
    grep -qE "^#+[[:space:]]*${sec}[[:space:]]" "$expected" || missing+=("$sec")
  done
  if [ -f Dockerfile ] && ! grep -qE '^#+[[:space:]]*1\.7[[:space:]]' "$expected"; then
    missing+=("1.7")
  fi
  if [ ${#missing[@]} -gt 0 ]; then
    stage handbook failed
    fail "手册缺章节：${missing[*]}。骨架见 references/manual.md"
    return
  fi

  # 事实字段：这几项 Skill 有能力查证，缺了就是没写全
  local fact_missing=()
  grep -qE '^#+[[:space:]]*1\.5' "$expected" && ! grep -qE '平台覆盖|flag ?文件位置|Flag ?文件' "$expected" \
    && fact_missing+=("1.5 旗帜信息（平台覆盖方式 / flag 文件位置）")
  grep -qE '^#+[[:space:]]*1\.6' "$expected" && ! grep -qE '端口|账号|地址' "$expected" \
    && fact_missing+=("1.6 题目情况（端口 / 账号 / 地址）")
  if [ ${#fact_missing[@]} -gt 0 ]; then
    stage handbook partial
    partial "手册事实字段不全：${fact_missing[*]}。这几项能从源码和配置读出来，不该缺"
    return
  fi

  if grep -qE '常见失败现象|常见问题排查' "$expected"; then
    stage handbook partial
    partial "手册里有常见失败现象这一节，这一节不写进交付手册"
    return
  fi
  # 部署命令里没带 /start.sh 是最常见的漏写，平台就是按这个启动的
  if [ -f Dockerfile ] && ! grep -qE 'docker run[^`]*start\.sh' "$expected"; then
    stage handbook partial
    partial "手册 1.7 的 docker run 命令没带 /start.sh，平台按 /start.sh 启动容器，手册要和平台一致"
    return
  fi

  # TODO 残留：判断部分本来就该留空给人工写，所以不算失败，如实报出来让人知道还缺什么。
  todo=$(grep -c 'TODO(人工填写)' "$expected" 2>/dev/null || echo 0)
  [ -z "$todo" ] && todo=0
  if [ "$todo" -gt 0 ]; then
    stage handbook "todo: $todo"
    echo "   手册结构齐全，判断部分有 ${todo} 处待人工填写"
    hint "手册 $todo 处 TODO(人工填写) 还没填：1.2 题目描述、1.4 考察信息、1.8 题目设计、1.9 解题步骤属于判断部分，由人工填写。这不是验证失败，交付前如实告知用户哪几节还空着。"
    return
  fi
  echo "   手册 $(basename "$expected") 结构齐全，无待填项"
  stage handbook passed
}

# provenance 是必填的，写成 pending 或者 verify 空着等于把"没证据"伪装成"待整理"。
# 老题没有这个字段时不报——那是历史包袱，不是这次没做；有新题忘了写才值得说。
assert_provenance() {
  [ -f challenge.yaml ] || return 0
  if grep -qE '^provenance:' challenge.yaml; then
    if grep -qE '^[[:space:]]+status:[[:space:]]*pending[[:space:]]*$' challenge.yaml; then
      stage provenance loaded
      fail "provenance.status 是 pending。它只能取 original_adapter / independent_completion / incomplete / attachment_only，没定下来就先别交付"
      return
    fi
    if grep -qE '^[[:space:]]+verify:[[:space:]]*(""|'"''"'|[[:space:]]*)$' challenge.yaml; then
      stage provenance loaded
      fail "provenance.verify 是空的。填 passed / environment_failed / incomplete，空着等于没给结论"
      return
    fi
    stage provenance passed
  fi
}


echo "== 检查手册"
assert_handbook
echo "== 检查 provenance"
assert_provenance

echo "== 检查交付目录"
shopt -s nullglob dotglob
EXTRA=()
for entry in "$PROJECT"/*; do
  name=$(basename "$entry")
  whitelisted "$name" || EXTRA+=("$name")
done
if [ ${#EXTRA[@]} -gt 0 ]; then
  echo "   多余文件："
  for e in "${EXTRA[@]}"; do echo "   - $e"; done
  # 报告和验证脚本副本是习惯性残留，直接判 failed；其余堆在 partial 里提醒。
  HARD_EXTRA=()
  for e in "${EXTRA[@]}"; do
    case "$e" in
      verify.sh|*verify.json|verify-report.json|*.pyc|__pycache__|.venv) HARD_EXTRA+=("$e");;
    esac
  done
  if [ ${#HARD_EXTRA[@]} -gt 0 ]; then
    stage delivery failed
    fail "交付目录里有不该出现的文件：${HARD_EXTRA[*]}。交付目录只留 Skill 白名单里的内容，报告写到系统临时目录"
  else
    stage delivery partial
    partial "交付目录有多余文件：${EXTRA[*]}。确认它们是不是交付物，不是就删掉"
  fi
else
  echo "   干净"
  stage delivery passed
fi

# RDG 题：有 check/check.sh 或 challenge.yaml 里 check.enabled，走 check 判定而不是 Flag 判定。
RDG=0
[ "$FORCE_RDG" = 1 ] && RDG=1
if [ -z "$CHECK" ] && [ -f "${PROJECT}/check/check.sh" ]; then CHECK="./check/check.sh"; fi
if [ -n "$CHECK" ]; then RDG=1; fi
if [ "$RDG" = 0 ] && [ -f challenge.yaml ] \
   && grep -qE '^[[:space:]]*check:[[:space:]]*$' challenge.yaml \
   && grep -qE 'enabled:[[:space:]]*true' challenge.yaml; then
  [ -f "${PROJECT}/check/check.sh" ] && CHECK="./check/check.sh" && RDG=1
fi

# ---------- 构建前的静态检查：这些问题会让容器起不来，提前说清楚比翻日志快
if [ ! -f Dockerfile ]; then
  # 附件题：没有容器，只检查交付结构和解题脚本。
  if [ -f "${PROJECT}/solve/solve.py" ] || [ -d "${PROJECT}/附件" ]; then
    echo "== 附件题（没有 Dockerfile，跳过容器验证）"
    ATT=("${PROJECT}/附件"/*)
    if [ ${#ATT[@]} -eq 0 ]; then
      partial "附件/ 是空的，确认选手该拿到哪些文件"
    else
      echo "   附件 ${#ATT[@]} 个"
      for a in "${ATT[@]}"; do echo "   - $(basename "$a")"; done
      stage attachments passed
    fi
    assert_handbook
    assert_provenance
    # 附件题也要用解题脚本确认题目真的能解，否则只证明目录结构像附件题。
    if [ -f "${PROJECT}/solve/solve.py" ]; then
      echo "== 运行解题脚本"
      if ! ( cd "$PROJECT" && python3 solve/solve.py ) >"$SOLVELOG" 2>&1; then
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

TESTFLAG="flag{verify_$(od -An -N6 -tx1 /dev/urandom | tr -d ' \n')}"
if [ "$RDG" = 1 ] && [ "$NO_FLAG_CONTRACT" = 1 ]; then
  # 有些 RDG 题的判据是题目自己配置里的固定目标，本来就没有 Flag 合同，不算缺项。
  echo "== 跳过 Flag 写入（RDG 题没有 Flag 合同，判据由 check 脚本给出）"
  stage flag_write skipped
else
  echo "== 写入测试 Flag 到 ${FLAGPATH}"
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

# ---------- RDG 判定：跑一遍判题脚本，初始环境必须"有漏洞"才算题目状态正确
# 判据不是 Flag，而是"漏洞还在不在"，和普通题是两套逻辑。
if [ "$RDG" = 1 ]; then
  echo "== 运行 RDG 判题脚本: $CHECK"
  # check.sh 没有执行位时，平台按 ./check.sh 调用会报 Permission denied，返回码非 0 会被当成
  # "有漏洞"——正好是 RDG 的预期结果，于是这个配置错误会被静默吞掉。先单独查出来。
  CHECKS_FOR_EXEC=$(printf '%s' "$CHECK" | sed 's/^\.\///')
  if [ -f "$CHECKS_FOR_EXEC" ] && [ ! -x "$CHECKS_FOR_EXEC" ]; then
    stage check_initial failed
    fail "check.sh 没有执行权限（${CHECKS_FOR_EXEC}）。平台按 ./check.sh 调用会报 Permission denied，加上执行位：chmod +x ${CHECKS_FOR_EXEC}"
    finish
  fi
  if [ -z "$FIRST_HOSTPORT" ]; then
    stage check_initial skipped
    partial "没有可用端口，跳过 RDG 判题"
  else
    ( cd "$PROJECT" && env TARGET_IP=127.0.0.1 TARGET_PORT="$FIRST_HOSTPORT" \
        "${SOLVE_ENV[@]+"${SOLVE_ENV[@]}"}" sh -c "$CHECK 127.0.0.1 $FIRST_HOSTPORT" ) >"$CHECKLOG" 2>&1
    CHECK_SRC=$?
    tail -40 "$CHECKLOG" | sed 's/^/   | /'
    # 初始环境预期是"有漏洞"，也就是脚本返回非 0。返回 0 说明漏洞本来就不存在。
    if [ "$CHECK_SRC" = 0 ]; then
      stage check_initial "ok: True"
      fail "RDG 判题脚本在初始环境就报已修复（返回 0）。选手没得打，先确认题目初始状态和 check 判定是不是反了"
    else
      stage check_initial "ok: False"
      echo "   初始环境判定为「有漏洞」，符合 RDG 预期"
    fi
  fi

  # 有解题脚本时顺手跑一遍：check 只证明"漏洞还在"，solve.py 才证明"这条链真的打得通"。
  # 拿到刚写入的测试 Flag 才算通过；没解出只记提示，不当失败——RDG 的正式判据是 check。
  if [ -n "$SOLVE" ] && [ -n "$FIRST_HOSTPORT" ]; then
    echo "== 运行 RDG 解题脚本: $SOLVE"
    sleep 2
    ( cd "$PROJECT" && env HOST=127.0.0.1 PORT="$FIRST_HOSTPORT" "${SOLVE_ENV[@]+"${SOLVE_ENV[@]}"}" \
        sh -c "$SOLVE" ) >"$SOLVELOG" 2>&1 &
    SPID=$!; T0=$(date +%s)
    while kill -0 "$SPID" 2>/dev/null && [ $(( $(date +%s) - T0 )) -lt "$SOLVE_TIMEOUT" ]; do sleep 1; done
    kill "$SPID" 2>/dev/null
    wait "$SPID" 2>/dev/null
    if grep -qF "$TESTFLAG" "$SOLVELOG"; then
      echo "   漏洞链打通，拿到测试 Flag"
      stage solve passed
    else
      tail -10 "$SOLVELOG" | sed 's/^/   | /'
      stage solve "no flag"
      hint "RDG 解题脚本没有拿到测试 Flag，确认漏洞链是通的（check 只说明漏洞存在）"
    fi
  fi
  finish
fi

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
