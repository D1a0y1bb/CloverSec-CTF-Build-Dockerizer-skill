# syntax=docker/dockerfile:1
FROM debian:bookworm-slim

RUN set -eux; \
    if command -v apk >/dev/null 2>&1; then \
      apk add --no-cache \
        bash ca-certificates \
        apache2 php php-apache2 \
        mariadb mariadb-client; \
    elif command -v apt-get >/dev/null 2>&1; then \
      apt-get update && apt-get install -y --no-install-recommends \
        bash ca-certificates \
        apache2 php libapache2-mod-php \
        mariadb-server mariadb-client \
      && rm -rf /var/lib/apt/lists/*; \
    else \
      echo "[ERROR] 当前基础镜像不支持 apk/apt-get，无法安装 LAMP 依赖" >&2; \
      exit 1; \
    fi

WORKDIR /var/www/html

COPY . /var/www/html

COPY start.sh /start.sh
RUN chmod 555 /start.sh
COPY flag /flag
RUN chmod 444 /flag
EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=10s CMD bash -lc 'echo > /dev/tcp/127.0.0.1/80'
CMD ["/start.sh"]
