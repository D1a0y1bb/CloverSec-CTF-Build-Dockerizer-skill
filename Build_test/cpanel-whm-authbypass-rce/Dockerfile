FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# python:3.11-slim 已包含 /bin/bash。保留条件安装逻辑，兼容基础镜像变化。
RUN if ! command -v bash >/dev/null 2>&1; then \
      apt-get update && \
      apt-get install -y --no-install-recommends bash && \
      rm -rf /var/lib/apt/lists/*; \
    fi

WORKDIR /opt/whm

COPY app/whm_mock.py /opt/whm/whm_mock.py
COPY app/cert.placeholder /opt/whm/cert.pem
COPY app/key.placeholder /opt/whm/key.pem
COPY flag /flag
COPY changeflag.sh /changeflag.sh
COPY start.sh /start.sh

RUN chmod 555 /start.sh /changeflag.sh && \
    mkdir -p /usr/local/cpanel/logs /usr/local/cpanel/Cpanel/Session /var/cpanel/sessions/raw /var/cpanel/sessions/root && \
    printf '%s\n' '11.110.0.89' > /usr/local/cpanel/version && \
    touch /usr/local/cpanel/logs/access_log /usr/local/cpanel/logs/error_log && \
    chmod 444 /flag && \
    chown root:root /flag /opt/whm/key.pem /opt/whm/cert.pem && \
    chmod 600 /opt/whm/key.pem && \
    chmod 644 /opt/whm/cert.pem

EXPOSE 2087

HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=10s \
  CMD bash -lc 'echo > /dev/tcp/127.0.0.1/2087'

ENTRYPOINT ["/start.sh"]
