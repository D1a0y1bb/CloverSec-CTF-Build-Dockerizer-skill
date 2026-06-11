# Bundle Recipe Schema

`bundle.yaml` describes a single-container multi-service recipe. It is not a package manager and it is not a replacement for `scenario.yaml`.

## Boundary

- `baseunit`: one standalone service component.
- `bundle`: one Docker image containing a small service recipe.
- `scenario`: local compose-style orchestration that keeps every service as its own final delivery directory.

## Input

```yaml
bundle:
  name: legacy-centos7-webstack
  recipe: legacy-centos7-python39-mysql57-redis5
  app_src: app
```

The first prototype also supports exact matching without `recipe`:

```yaml
bundle:
  name: legacy-centos7-webstack
  base_os: centos:7
  mode: single_container
  services:
    - id: mysql
      version: "5.7"
    - id: redis
      version: "5.0"
    - id: python
      version: "3.9"
```

Unsupported combinations must return `BUNDLE_UNSUPPORTED_COMBINATION` instead of silently choosing another stack.

## Custom Explicit Bundle

When no fixed recipe matches, `render_bundle.py` can render a custom explicit bundle if the input provides all required delivery decisions:

```yaml
bundle:
  name: bundle-custom-explicit
  recipe: custom
  base_image: debian:bookworm-slim
  workdir: /opt/bundle/app
  app_src: app
  app_dst: /opt/bundle/app
  expose_ports: ["8080", "6379"]
  install_commands:
    - apt-get update && apt-get install -y --no-install-recommends bash python3 redis-server
    - rm -rf /var/lib/apt/lists/*
  start_commands:
    - cmd: redis-server --protected-mode no --bind 0.0.0.0
      mode: background
    - cmd: python3 -m http.server 8080 --bind 0.0.0.0
      mode: foreground
  healthcheck_cmd: bash -lc 'echo > /dev/tcp/127.0.0.1/8080'
  services:
    - id: redis
      version: "7"
      role: cache
    - id: python
      version: "3"
      role: app_runtime
  startup_order: ["redis", "python"]
```

Custom bundle rules:

- `base_image`、`expose_ports`、`services`、`start_commands` are required.
- `start_commands` supports `mode: background|foreground|wait`; `foreground` or `wait` must be the final step.
- `install_commands` are copied into Dockerfile as provided. The Skill does not infer package names or solve versions.
- Incomplete custom input still returns `BUNDLE_UNSUPPORTED_COMBINATION`.

## Generated Delivery

`render_bundle.py` writes a standard delivery directory:

```text
Dockerfile
start.sh
changeflag.sh
flag
challenge.yaml
app/
```

The generated `challenge.yaml` uses:

- `challenge.stack: bundle`
- `challenge.profile: jeopardy`
- `challenge.support_level: partial`
- `challenge.bundle.recipe_id`

Docker build and runtime validation are manual for old dependency stacks.
