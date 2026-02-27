{{> snippets/docker-common-prolog.tpl }}

# Node.js 最小模板：适用于原生 HTTP/Express/Koa/Fastify 等 Web 题目
{{> snippets/run-bash-bootstrap.tpl }}

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

{{> snippets/docker-common-epilog.tpl }}
