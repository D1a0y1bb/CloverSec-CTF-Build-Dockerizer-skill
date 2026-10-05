# syntax=docker/dockerfile:1
FROM debian:bookworm-slim

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

WORKDIR /opt/linux-qemu

COPY . /opt/linux-qemu

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

COPY start.sh /start.sh
COPY changeflag.sh /changeflag.sh
COPY flag /flag

RUN chmod 555 /start.sh && chmod 555 /changeflag.sh && chmod 444 /flag
EXPOSE 22

HEALTHCHECK --interval=30s --timeout=10s --retries=5 --start-period=90s CMD bash -lc 'timeout 8 bash -c "cat < /dev/tcp/127.0.0.1/22" | head -c 4 | grep -q SSH-'
CMD ["/start.sh"]
