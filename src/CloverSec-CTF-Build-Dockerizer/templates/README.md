# templates 模板库（v3.0）

## 栈模板目录

- `node/`
- `php/`
- `python/`
- `java/`
- `tomcat/`
- `lamp/`
- `pwn/`
- `ai/`
- `rdg/`
- `secops/`
- `linux-qemu/`
- `baseunit/`

每个栈目录包含：

- `Dockerfile.tpl`
- `start.sh.tpl`
- `README.md`（如有）

## snippets

关键片段：

- `copy-flag-start.tpl`：旧 helper 合同的 `/start.sh + /changeflag.sh + /flag` 产物落地
- `docker-common-prolog.tpl` / `docker-common-epilog.tpl`
- `start-header.tpl`
- `healthcheck.tpl`
- `defense-docker-block.tpl`
- `defense-start-block.tpl`
- `ensure-flag.tpl`

## v3 规则

- 模板渲染后不得保留未替换变量
- direct-exec 默认只生成 `/start.sh`，并按 `flag.path` 处理可选初始 flag
- `/changeflag.sh` 只在 `helper_script`、`qemu_guest` 或旧平台合同中生成
- `include_flag_artifact=false` 只控制初始 flag 文件，不会强制生成 helper
- `rdg/secops` 使用专用模板语义；其他栈在 profile 需要时注入 defense block
- `linux-qemu` 使用专用 VM/QEMU 变量；默认不要求 `/dev/kvm` 或 `--privileged`
