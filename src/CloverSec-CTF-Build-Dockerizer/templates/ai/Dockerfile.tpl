{{> snippets/docker-common-prolog.tpl }}

# AI 最小模板：默认 CPU 推理服务，优先 gunicorn 前台运行
{{> snippets/run-bash-bootstrap.tpl }}

# 可选运行时依赖安装。
RUN set -eux; \
    {{RUNTIME_DEPS_INSTALL}}

# 工作目录统一由模板变量控制。
{{> snippets/workdir.tpl }}

# 复制应用代码。
COPY {{APP_SRC}} {{APP_DST}}
{{COPY_APP}}

# 默认收紧数值计算线程，规避高核心宿主机线程创建失败。
ENV OPENBLAS_NUM_THREADS=1 \
    OMP_NUM_THREADS=1 \
    NUMEXPR_NUM_THREADS=1 \
    GOTO_NUM_THREADS=1 \
    MKL_NUM_THREADS=1 \
    MALLOC_ARENA_MAX=2 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 可选额外环境变量。
{{> snippets/env.tpl }}

# Python 依赖安装必须使用 --no-cache-dir 以控制镜像体积。
{{PIP_REQUIREMENTS_BLOCK}}

{{> snippets/docker-common-epilog.tpl }}
