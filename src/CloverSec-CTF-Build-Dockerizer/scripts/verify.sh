#!/usr/bin/env bash
# verify.sh —— 对一个题目交付目录做真实验证：构建、启动、写测试 Flag、探测入口、清理。
#
# 用法：
#   bash scripts/verify.sh <题目目录> [--port N] [--flag-path P] [--keep]
#
# 它只做"能不能跑"的验证，不改你的交付文件。结果如实报告：
#   passed      构建、启动、Flag 回读、端口探测都过了
#   partial     起来了但有项没验到（会说清哪项）
#   failed      构建或启动失败
set -uo pipefail

PROJECT="${1:-}"
[ -z "$PROJECT" ] && { echo "用法: bash scripts/verify.sh <题目目录> [--port N] [--flag-path P] [--keep]"; exit 2; }
shift || true

PORT=""; FLAGPATH=""; KEEP=0
while [ $# -gt 0 ]; do
  case "$1" in
    --port) PORT="$2"; shift 2;;
    --flag-path) FLAGPATH="$2"; shift 2;;
    --keep) KEEP=1; shift;;
    *) echo "未知参数: $1"; exit 2;;
  esac
done

cd "$PROJECT" || { echo "目录不存在: $PROJECT"; exit 2; }
[ -f Dockerfile ] || { echo "failed: 没有 Dockerfile"; exit 1; }

YAML="challenge.yaml"
# 从 challenge.yaml 兜底提取端口和 flag 路径（命令行参数优先）。
if [ -f "$YAML" ]; then
  [ -z "$PORT" ] && PORT=$(grep -A3 -E 'expose_ports' "$YAML" | grep -oE '[0-9]+' | head -1)
  [ -z "$FLAGPATH" ] && FLAGPATH=$(grep -E '^[[:space:]]*path:' "$YAML" | head -1 | sed -E 's/.*path:[[:space:]]*//; s/["'"'"' ]//g')
fi
[ -z "$FLAGPATH" ] && FLAGPATH="/flag"

IMAGE="ctf-verify-$(basename "$PROJECT" | tr '[:upper:] ' '[:lower:]-'):test"
CONTAINER="ctf-verify-$$"
STATUS="passed"; NOTES=()

cleanup() {
  [ "$KEEP" = "1" ] && { echo "[keep] 保留容器 $CONTAINER 和镜像 $IMAGE"; return; }
  docker rm -f "$CONTAINER" >/dev/null 2>&1
  docker rmi "$IMAGE" >/dev/null 2>&1
}
trap cleanup EXIT

echo "== 构建镜像 $IMAGE"
docker build -t "$IMAGE" . || { echo "failed: docker build 失败"; exit 1; }

echo "== 启动容器"
if [ -n "$PORT" ]; then
  docker run -d --name "$CONTAINER" -p "$PORT" "$IMAGE" /start.sh >/dev/null 2>&1 \
    || docker run -d --name "$CONTAINER" -P "$IMAGE" /start.sh >/dev/null 2>&1 \
    || { echo "failed: 容器启动失败"; docker logs "$CONTAINER" 2>&1 | tail -20; exit 1; }
else
  docker run -d --name "$CONTAINER" "$IMAGE" /start.sh >/dev/null 2>&1 \
    || { echo "failed: 容器启动失败"; exit 1; }
fi

sleep 2
if [ "$(docker inspect -f '{{.State.Running}}' "$CONTAINER" 2>/dev/null)" != "true" ]; then
  echo "failed: 容器未保持运行（start.sh 可能没前台拉起服务）"
  docker logs "$CONTAINER" 2>&1 | tail -20
  exit 1
fi
echo "   容器运行中"

# 写一个测试 Flag，再读回，验证 flag.path 可写可读、程序能看到。
echo "== 写测试 Flag 到 $FLAGPATH"
TESTFLAG="flag{verify_$(date +%s)}"
if docker exec "$CONTAINER" sh -c "echo '$TESTFLAG' > '$FLAGPATH' 2>/dev/null"; then
  BACK=$(docker exec "$CONTAINER" sh -c "cat '$FLAGPATH' 2>/dev/null" | tr -d '\r\n')
  [ "$BACK" = "$TESTFLAG" ] && echo "   Flag 回读一致" || { STATUS="partial"; NOTES+=("Flag 回读不一致"); }
else
  STATUS="partial"; NOTES+=("无法写入 $FLAGPATH（权限或路径问题）")
fi

# 探测对外端口：HTTP 优先，退化到 TCP 连通性。
if [ -n "$PORT" ]; then
  HOSTPORT=$(docker port "$CONTAINER" 2>/dev/null | head -1 | sed -E 's/.*:([0-9]+)$/\1/')
  if [ -n "$HOSTPORT" ]; then
    echo "== 探测端口 localhost:$HOSTPORT"
    OK=0
    for i in $(seq 1 10); do
      CODE=$(curl -s -o /dev/null -w '%{http_code}' "http://localhost:$HOSTPORT/" 2>/dev/null)
      if [ -n "$CODE" ] && [ "$CODE" != "000" ]; then echo "   HTTP $CODE"; OK=1; break; fi
      if nc -z localhost "$HOSTPORT" 2>/dev/null; then echo "   TCP 可连通"; OK=1; break; fi
      sleep 1
    done
    [ "$OK" = "1" ] || { STATUS="partial"; NOTES+=("端口 $HOSTPORT 无响应"); }
  else
    STATUS="partial"; NOTES+=("端口未映射，跳过探测")
  fi
else
  STATUS="partial"; NOTES+=("challenge.yaml 无端口，跳过探测")
fi

echo
echo "== 结果: $STATUS"
for n in "${NOTES[@]:-}"; do [ -n "$n" ] && echo "   - $n"; done
[ "$STATUS" = "passed" ] && exit 0 || exit 0
