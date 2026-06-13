# syntax=docker/dockerfile:1
FROM debian:bookworm-slim


# Linux kernel QEMU VM 模板：外层 Docker 承载 QEMU，guest 承载 vulnerable kernel/rootfs。
RUN set -eux; \
    if command -v apt-get >/dev/null 2>&1; then \
      apt-get update && apt-get install -y --no-install-recommends \
        bash ca-certificates e2fsprogs iproute2 openssh-client procps \
        qemu-system-arm qemu-system-x86 qemu-utils xz-utils && \
      rm -rf /var/lib/apt/lists/*; \
    else \
      echo "[ERROR] linux-qemu 模板当前仅支持 apt 系基础镜像" >&2; \
      exit 1; \
    fi

RUN set -eux; \
    :

# 统一工作目录：start.sh 会切换到该目录
WORKDIR /opt/linux-qemu


COPY . /opt/linux-qemu
# no extra copy

RUN set -eux; \
    if [ "prebuilt" = "build-script" ]; then \
      test -f "/opt/linux-qemu/scripts/build-vm.sh"; \
      chmod +x "/opt/linux-qemu/scripts/build-vm.sh"; \
      "/opt/linux-qemu/scripts/build-vm.sh"; \
    fi; \
    test -f "/opt/linux-qemu/vm/vmlinuz"; \
    VM_INITRD=""; \
    if [ -n "$VM_INITRD" ]; then test -f "/opt/linux-qemu/$VM_INITRD"; fi; \
    test -f "/opt/linux-qemu/vm/rootfs.ext4"

# no docker env


# defense block disabled

# defense block disabled
# ---- 平台硬约束：/start.sh /changeflag.sh 与 /flag 必须位于容器根目录 ----
COPY start.sh /start.sh
COPY changeflag.sh /changeflag.sh
COPY flag /flag

# /start.sh 与 /changeflag.sh 必须可执行；/flag 必须可读（平台启动后会写入动态 flag）
RUN chmod 555 /start.sh && chmod 555 /changeflag.sh && chmod 444 /flag
# 对外暴露端口（至少一个）
EXPOSE 22

HEALTHCHECK --interval=30s --timeout=10s --retries=5 --start-period=90s CMD bash -lc 'timeout 8 bash -c "cat < /dev/tcp/127.0.0.1/22" | head -c 4 | grep -q SSH-'
# 默认启动入口，便于本地直接 docker run image
CMD ["/start.sh"]
