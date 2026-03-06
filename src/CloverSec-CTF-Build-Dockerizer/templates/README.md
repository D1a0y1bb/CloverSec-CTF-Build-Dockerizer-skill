# templates 模板库（v2.0.2）

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
- `baseunit/`

每个栈目录包含：

- `Dockerfile.tpl`
- `start.sh.tpl`
- `README.md`（如有）

## snippets

关键片段：

- `copy-flag-start.tpl`：`/start.sh + /changeflag.sh + /flag` 产物落地
- `docker-common-prolog.tpl` / `docker-common-epilog.tpl`
- `start-header.tpl`
- `healthcheck.tpl`
- `defense-docker-block.tpl`
- `defense-start-block.tpl`
- `ensure-flag.tpl`

## V2 规则

- 模板渲染后不得保留未替换变量
- `/changeflag.sh` 必须参与交付
- `include_flag_artifact=false` 仅放行 `flag`，不放行 `changeflag`
- `rdg/secops` 使用专用模板语义；其他栈在 profile 需要时注入 defense block
