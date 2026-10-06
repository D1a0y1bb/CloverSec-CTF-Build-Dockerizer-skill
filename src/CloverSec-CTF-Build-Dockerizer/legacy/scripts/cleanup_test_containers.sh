#!/usr/bin/env bash
set -euo pipefail

if ! command -v docker >/dev/null 2>&1; then
  echo "[ERROR] 未检测到 docker 命令" >&2
  exit 2
fi

container_ids="$(docker ps -a --filter "name=ctf-skill-test-" --format '{{.ID}}' || true)"
if [[ -n "$container_ids" ]]; then
  echo "清理测试容器..."
  # shellcheck disable=SC2086
  docker rm -f $container_ids >/dev/null 2>&1 || true
fi

image_refs="$(docker images "ctf-skill-test*" --format '{{.Repository}}:{{.Tag}}' || true)"
if [[ -n "$image_refs" ]]; then
  echo "清理测试镜像..."
  while IFS= read -r image; do
    [[ -n "$image" ]] || continue
    docker rmi "$image" >/dev/null 2>&1 || true
  done <<< "$image_refs"
fi

echo "[OK] 测试容器与镜像清理完成"
