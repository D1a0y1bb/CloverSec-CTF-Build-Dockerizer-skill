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
  if command -v mariadb-install-db >/dev/null 2>&1; then
    mariadb-install-db --user=mysql --datadir=/var/lib/mysql >/dev/null
  elif command -v mysql_install_db >/dev/null 2>&1; then
    mysql_install_db --user=mysql --datadir=/var/lib/mysql >/dev/null
  fi
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

START_CMD="httpd -D FOREGROUND"
DEFAULT_HTTPD_CMD=""
if command -v apache2ctl >/dev/null 2>&1; then
  DEFAULT_HTTPD_CMD="apache2ctl -D FOREGROUND"
elif command -v httpd >/dev/null 2>&1; then
  DEFAULT_HTTPD_CMD="httpd -D FOREGROUND"
else
  echo "[ERROR] 未检测到 apache2ctl/httpd，可用前台 Web 服务命令缺失" >&2
  exit 1
fi

if [[ -z "${START_CMD}" ]]; then
  START_CMD="${DEFAULT_HTTPD_CMD}"
fi

if [[ "${START_CMD}" == "apache2ctl -D FOREGROUND" ]] && ! command -v apache2ctl >/dev/null 2>&1; then
  START_CMD="${DEFAULT_HTTPD_CMD}"
fi

echo "[INFO] exec: ${START_CMD}"
exec bash -lc "${START_CMD}"
