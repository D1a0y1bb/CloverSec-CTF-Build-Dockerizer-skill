# python-loopback-ssrf-basic

- 目的：覆盖 `platform.allow_loopback_bind=true` 的 SSRF/内网链路豁免场景。
- 关键点：启动命令显式监听 `127.0.0.1`，并禁用 Docker HEALTHCHECK。
