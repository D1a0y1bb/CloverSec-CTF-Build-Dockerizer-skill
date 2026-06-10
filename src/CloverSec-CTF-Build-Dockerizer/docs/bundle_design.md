# Bundle / Recipe Design

Bundle recipes cover old single-container web stacks that are too broad for BaseUnit but should not be modeled as Scenario compose output.

## Current Prototype

Supported recipes:

- `legacy-centos7-python39-mysql57-redis5`
- `tomcat85-jdk8-mysql57`

Both are `support_level: partial`. They generate platform-shaped delivery files and pass static contract validation, but old package repositories may require operator work before Docker build.

## Non-goals

- No arbitrary version solver.
- No automatic cPanel/WHM installation.
- No conversion of compose files into final platform delivery.

cPanel/WHM-like input should stay on `bundle_recipe` or manual review until a dedicated recipe exists.

## Validation

Use:

```bash
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/render_bundle.py --recipe legacy-centos7-python39-mysql57-redis5 --output /tmp/bundle
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/validate_bundle.py --bundle-dir /tmp/bundle
bash src/CloverSec-CTF-Build-Dockerizer/scripts/validate.sh /tmp/bundle/Dockerfile /tmp/bundle/start.sh /tmp/bundle/challenge.yaml
```
