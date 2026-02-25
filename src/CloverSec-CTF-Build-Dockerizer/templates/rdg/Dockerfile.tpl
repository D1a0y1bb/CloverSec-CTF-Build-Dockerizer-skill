# syntax=docker/dockerfile:1
# RDG 最小模板：兼容题目服务 + ttyd 旁路（存在即启用）
FROM {{BASE_IMAGE}}

# 平台契约依赖 bash；RDG 常见调试链路依赖 curl/sudo/procps。
RUN set -eux; \
    if command -v apk >/dev/null 2>&1; then \
      apk add --no-cache bash ca-certificates curl sudo shadow procps; \
    elif command -v apt-get >/dev/null 2>&1; then \
      apt-get update && apt-get install -y --no-install-recommends bash ca-certificates curl sudo procps && rm -rf /var/lib/apt/lists/*; \
    else \
      echo "[ERROR] 当前基础镜像不支持 apk/apt-get，无法安装 RDG 依赖" >&2; \
      exit 1; \
    fi

# 可选运行时依赖安装。
RUN set -eux; \
    {{RUNTIME_DEPS_INSTALL}}

# RDG 建议创建 ctf 用户（best-effort，不强阻断）。
RUN set -eux; \
    if ! id ctf >/dev/null 2>&1; then \
      if command -v useradd >/dev/null 2>&1; then \
        useradd -m -s /bin/bash ctf; \
      elif command -v adduser >/dev/null 2>&1; then \
        adduser -D -s /bin/bash ctf; \
      fi; \
    fi

{{> snippets/workdir.tpl }}

# 复制题目业务文件。
COPY {{APP_SRC}} {{APP_DST}}
{{COPY_APP}}

{{> snippets/env.tpl }}

# 平台硬约束文件。
{{> snippets/copy-flag-start.tpl }}
{{> snippets/expose.tpl }}
{{> snippets/cmd-start.tpl }}
