{{> snippets/docker-common-prolog.tpl }}

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
    {{RUNTIME_DEPS_INSTALL}}

{{> snippets/workdir.tpl }}

COPY {{APP_SRC}} {{APP_DST}}
{{COPY_APP}}

RUN set -eux; \
    if [ "{{VM_ASSET_MODE}}" = "build-script" ]; then \
      test -f "{{WORKDIR}}/{{VM_BUILD_SCRIPT}}"; \
      chmod +x "{{WORKDIR}}/{{VM_BUILD_SCRIPT}}"; \
      "{{WORKDIR}}/{{VM_BUILD_SCRIPT}}"; \
    fi; \
    test -f "{{WORKDIR}}/{{VM_KERNEL}}"; \
    test -f "{{WORKDIR}}/{{VM_INITRD}}"; \
    test -f "{{WORKDIR}}/{{VM_ROOTFS}}"

{{> snippets/env.tpl }}

{{DEFENSE_DOCKER_BLOCK}}

{{> snippets/docker-common-epilog.tpl }}
