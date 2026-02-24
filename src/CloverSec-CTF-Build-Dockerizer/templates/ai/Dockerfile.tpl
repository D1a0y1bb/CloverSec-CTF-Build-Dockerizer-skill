# syntax=docker/dockerfile:1
# AI 最小模板：默认 CPU 推理服务，优先 gunicorn 前台运行
FROM {{BASE_IMAGE}}

# 平台动态 flag 注入要求 /bin/bash，需兼容 apt/apk 两类基础镜像。
RUN set -eux; \
    if command -v apk >/dev/null 2>&1; then \
      {{> snippets/apk-install-bash.tpl }}; \
    elif command -v apt-get >/dev/null 2>&1; then \
      {{> snippets/apt-install-bash.tpl }}; \
    else \
      echo "[ERROR] 当前基础镜像不支持 apk/apt-get，无法安装 bash" >&2; \
      exit 1; \
    fi

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

# 平台硬约束文件。
{{> snippets/copy-flag-start.tpl }}

# 暴露服务端口（默认 5000）。
{{> snippets/expose.tpl }}

# 保持与平台一致的默认入口。
{{> snippets/cmd-start.tpl }}
