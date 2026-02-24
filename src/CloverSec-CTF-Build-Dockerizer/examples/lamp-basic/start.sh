#!/bin/bash
set -euo pipefail


# LAMP 多服务启动：MariaDB 后台 + Apache 前台 exec。
# 保障 /flag 存在并保持可读，便于平台后续覆盖写入
if [ ! -f /flag ]; then
  touch /flag
fi
chmod 444 /flag || true

:


cd "/var/www/html"

mkdir -p /run/mysqld /var/log/mysql /var/log/apache2
chown -R mysql:mysql /run/mysqld /var/lib/mysql /var/log/mysql || true

if [[ ! -d /var/lib/mysql/mysql ]]; then
  echo "[INFO] 初始化 MariaDB 数据目录"
  mariadb-install-db --user=mysql --datadir=/var/lib/mysql >/dev/null
fi

echo "[INFO] 后台启动 MariaDB"
mariadbd --user=mysql --datadir=/var/lib/mysql --bind-address=127.0.0.1 >/var/log/mysql/error.log 2>&1 &

# 若注入了初始化 SQL（base64），在数据库就绪后执行一次。
if [[ -n "${MYSQL_INIT_SQL_B64:-}" ]]; then
  echo "${MYSQL_INIT_SQL_B64}" | base64 -d > /tmp/init.sql
  for i in {1..30}; do
    mariadb-admin ping -uroot >/dev/null 2>&1 && break
    sleep 1
  done
  mariadb -uroot < /tmp/init.sql || true
fi

# 输出真实日志，便于平台观测。
touch /var/log/apache2/access.log /var/log/apache2/error.log
ln -sf /proc/self/fd/1 /var/log/apache2/access.log
ln -sf /proc/self/fd/2 /var/log/apache2/error.log

START_CMD="apache2ctl -D FOREGROUND"
if [[ -z "${START_CMD}" ]]; then
  START_CMD="apache2ctl -D FOREGROUND"
fi

echo "[INFO] exec: ${START_CMD}"
exec bash -lc "${START_CMD}"
