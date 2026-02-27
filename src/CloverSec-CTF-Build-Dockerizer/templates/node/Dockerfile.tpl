# syntax=docker/dockerfile:1
# Node.js 最小模板：适用于原生 HTTP/Express/Koa/Fastify 等 Web 题目
FROM {{BASE_IMAGE}}

# 平台会执行 /bin/bash /changeflag.sh，必须保障 /bin/bash 存在。
RUN set -eux; \
    if command -v apk >/dev/null 2>&1; then \
      {{> snippets/apk-install-bash.tpl }}; \
    elif command -v apt-get >/dev/null 2>&1; then \
      {{> snippets/apt-install-bash.tpl }}; \
    else \
      echo "[ERROR] 当前基础镜像不支持 apk/apt-get，无法安装 bash" >&2; \
      exit 1; \
    fi

# 可选运行时依赖（无额外依赖时渲染为 :）。 
RUN set -eux; \
    {{RUNTIME_DEPS_INSTALL}}

# 工作目录统一由模板变量控制，便于 start.sh 与 Dockerfile 对齐。
{{> snippets/workdir.tpl }}

# 复制题目代码。
COPY {{APP_SRC}} {{APP_DST}}
{{COPY_APP}}

# 可选环境变量（为空时会渲染为注释或空操作）。
{{> snippets/env.tpl }}

# 依赖安装块由渲染器生成：有 lock 优先 npm ci，无 lock 回退 npm install。
{{NPM_INSTALL_BLOCK}}

# 平台硬约束文件。
{{> snippets/copy-flag-start.tpl }}

# 声明端口，便于平台映射与排障。
{{> snippets/expose.tpl }}

# 可选健康检查。
{{HEALTHCHECK_BLOCK}}

# 默认入口保持与平台一致。
{{> snippets/cmd-start.tpl }}
