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

- `docker-common-prolog.tpl`：统一 `FROM` 头部
- `docker-common-epilog.tpl`：统一 `flag/expose/healthcheck/cmd` 尾部
- `run-bash-bootstrap.tpl`：统一 bash 引导安装分支
- `copy-flag-start.tpl`：写入 `/start.sh` 与 `/flag` 并设置权限
- `expose.tpl`：渲染 `EXPOSE` 指令
- `healthcheck.tpl`：渲染 Docker `HEALTHCHECK` 指令
- `workdir.tpl`：渲染 `WORKDIR`
- `apt-install-bash.tpl`：Debian/Ubuntu 安装 bash + 清理 apt 缓存
- `apk-install-bash.tpl`：Alpine 安装 bash（`--no-cache`）
- `cmd-start.tpl`：默认 `CMD ["/start.sh"]`
- `env.tpl`：注入环境变量片段
- `start-header.tpl`：统一 shebang 与 `set -euo pipefail`
- `ensure-flag.tpl`：启动前确保 `/flag` 可读

说明：

- RDG 模板支持 `challenge.rdg.include_flag_artifact=false`，该模式下会改为仅写入 `/start.sh`，不再强制渲染 `/flag` 片段。
- 自 `v1.4.0-r1` 起，9 栈 Dockerfile 统一使用 prolog/epilog 组合片段，减少重复模板维护成本。
- 所有栈模板支持 `{{HEALTHCHECK_BLOCK}}` 注入，可通过 `challenge.healthcheck.enabled=false` 显式关闭。
- `pwn` 与 `lamp` 模板支持 Debian/Ubuntu 与 Alpine 双分支安装策略；`pwn` 同时支持 `xinetd/tcpserver/socat` 前台路径。
- `php/node/java` 的 `BASE_IMAGE` 可由运行时档位映射（`data/runtime_profiles.yaml`）生成，`--base-image` 仍可最终覆盖。

## include 语法

模板支持最小 include 语法，由 `render.py` 在渲染时内联：

```text
{{> snippets/copy-flag-start.tpl }}
```

变量采用 `{{VAR}}` 形式，具体字段由 `scripts/render.py` 提供。
