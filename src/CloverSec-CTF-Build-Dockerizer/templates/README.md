# templates 模板库

## 技术栈目录

- `node/`
- `php/`
- `python/`
- `java/`
- `tomcat/`
- `lamp/`
- `pwn/`
- `ai/`
- `rdg/`

每个技术栈目录都包含三类文件：

- `Dockerfile.tpl`：镜像构建模板
- `start.sh.tpl`：平台启动脚本模板
- `README.md`：变量说明、默认值、最小 challenge.yaml 示例

## snippets 目录

通用片段位于 `snippets/`：

- `copy-flag-start.tpl`：写入 `/start.sh` 与 `/flag` 并设置权限
- `expose.tpl`：渲染 `EXPOSE` 指令
- `workdir.tpl`：渲染 `WORKDIR`
- `apt-install-bash.tpl`：Debian/Ubuntu 安装 bash + 清理 apt 缓存
- `apk-install-bash.tpl`：Alpine 安装 bash（`--no-cache`）
- `cmd-start.tpl`：默认 `CMD ["/start.sh"]`
- `env.tpl`：注入环境变量片段
- `start-header.tpl`：统一 shebang 与 `set -euo pipefail`
- `ensure-flag.tpl`：启动前确保 `/flag` 可读

说明：RDG 模板支持 `challenge.rdg.include_flag_artifact=false`，该模式下会改为仅写入 `/start.sh`，不再强制渲染 `/flag` 片段。

## include 语法

模板支持最小 include 语法，由 `render.py` 在渲染时内联：

```text
{{> snippets/copy-flag-start.tpl }}
```

变量采用 `{{VAR}}` 形式，具体字段由 `scripts/render.py` 提供。
