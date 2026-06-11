# Bundle / Recipe Design

Bundle recipes cover old single-container web stacks that are too broad for BaseUnit but should not be modeled as Scenario compose output.

## Current Prototype

Fixed recipes:

- `legacy-centos7-python39-mysql57-redis5`
- `tomcat85-jdk8-mysql57`

Both are `support_level: partial`. They generate platform-shaped delivery files and pass static contract validation, but old package repositories may require operator work before Docker build.

Custom explicit recipes:

- Use `recipe: custom` or an unknown `recipe` plus all required fields.
- Required fields: `base_image`、`expose_ports`、`services`、`start_commands`。
- `install_commands` and `start_commands` come from the user. The renderer does not infer service package names, mirror settings, credentials or version compatibility.
- The generated `challenge.bundle.recipe_id` becomes `custom-<name>` unless the user provides a custom recipe id.

## Non-goals

- No arbitrary version solver.
- No automatic cPanel/WHM installation.
- No conversion of compose files into final platform delivery.
- No automatic package source repair for legacy distributions.

## Validation

Use:

```bash
python3 scripts/render_bundle.py --recipe legacy-centos7-python39-mysql57-redis5 --output /tmp/bundle
python3 scripts/validate_bundle.py --bundle-dir /tmp/bundle
bash scripts/validate.sh /tmp/bundle/Dockerfile /tmp/bundle/start.sh /tmp/bundle/challenge.yaml
```

Custom explicit example:

```bash
python3 scripts/render_bundle.py --config examples/bundle-custom-explicit/bundle.yaml --output /tmp/bundle-custom-explicit
python3 scripts/validate_bundle.py --bundle-dir /tmp/bundle-custom-explicit
bash scripts/validate.sh /tmp/bundle-custom-explicit/Dockerfile /tmp/bundle-custom-explicit/start.sh /tmp/bundle-custom-explicit/challenge.yaml
```
