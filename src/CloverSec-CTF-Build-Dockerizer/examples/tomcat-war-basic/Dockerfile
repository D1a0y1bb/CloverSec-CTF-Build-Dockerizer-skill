# syntax=docker/dockerfile:1
FROM tomcat:9.0-jre17-temurin-jammy


# Tomcat(WAR) 最小模板：适用于 ROOT.war 或 webapps 目录部署
RUN set -eux; \
    if command -v apk >/dev/null 2>&1; then \
      apk add --no-cache bash ca-certificates; \
    elif command -v apt-get >/dev/null 2>&1; then \
      apt-get update && apt-get install -y --no-install-recommends bash ca-certificates && rm -rf /var/lib/apt/lists/*; \
    else \
      echo "[ERROR] 当前基础镜像不支持 apk/apt-get，无法安装 bash" >&2; \
      exit 1; \
    fi


RUN set -eux; \
    :

# 统一工作目录：start.sh 会切换到该目录
WORKDIR /usr/local/tomcat


# 通常将 ROOT.war 放置到 /usr/local/tomcat/webapps/ROOT.war。
COPY ROOT.war /usr/local/tomcat/webapps/ROOT.war
# no extra copy

# no docker env


# ---- 平台硬约束：/start.sh 与 /flag 必须位于容器根目录 ----
COPY start.sh /start.sh
COPY flag /flag

# /start.sh 必须可执行；/flag 必须可读（平台启动后会写入动态 flag）
RUN chmod 555 /start.sh && chmod 444 /flag
# 对外暴露端口（至少一个）
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=10s CMD bash -lc 'echo > /dev/tcp/127.0.0.1/8080'
# 默认启动入口，便于本地直接 docker run image
CMD ["/start.sh"]
