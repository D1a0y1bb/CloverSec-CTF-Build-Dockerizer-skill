# syntax=docker/dockerfile:1.7
FROM debian:bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

RUN test "$(dpkg --print-architecture)" = "amd64"

RUN apt-get -o Acquire::Retries=5 update && \
    apt-get install -o Acquire::Retries=5 -y --no-install-recommends \
      bash \
      ca-certificates \
      debootstrap \
      e2fsprogs \
      iproute2 \
      openssh-client \
      procps \
      qemu-system-x86 \
      qemu-utils \
      xz-utils && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /opt/copyfail

COPY scripts/build-vm.sh /usr/local/bin/build-vm.sh
COPY flag /flag
COPY changeflag.sh /changeflag.sh
COPY start.sh /start.sh

RUN --mount=type=cache,target=/var/cache/copyfail-debootstrap \
    chmod 555 /usr/local/bin/build-vm.sh /start.sh /changeflag.sh && \
    chmod 444 /flag && \
    /usr/local/bin/build-vm.sh && \
    rm -rf /usr/local/bin/build-vm.sh /var/cache/apt/* /var/lib/apt/lists/*

EXPOSE 22

HEALTHCHECK --interval=30s --timeout=5s --retries=5 --start-period=90s \
  CMD bash -lc 'exec 3<>/dev/tcp/127.0.0.1/22 && IFS= read -r -t 3 line <&3 && [[ "$line" == SSH-* ]]'

ENTRYPOINT ["/start.sh"]
