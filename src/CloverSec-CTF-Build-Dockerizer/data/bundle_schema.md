# Bundle Recipe Schema

`bundle.yaml` describes a fixed single-container multi-service recipe. It is not a generic package manager and it is not a replacement for `scenario.yaml`.

## Boundary

- `baseunit`: one standalone service component.
- `bundle`: one Docker image containing a small, fixed service recipe.
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
