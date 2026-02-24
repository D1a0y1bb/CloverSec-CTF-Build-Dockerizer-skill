# CloverSec-CTF-Build-Dockerizer

[简体中文](README.md)

[![Version](https://img.shields.io/badge/version-v1.2.4-blue)](https://github.com/D1a0y1bb/CloverSec-CTF-Build-Dockerizer-skill/releases)
[![Scope](https://img.shields.io/badge/CTF-Jeopardy-2ea44f)](https://github.com/D1a0y1bb/CloverSec-CTF-Build-Dockerizer-skill)
[![Stacks](https://img.shields.io/badge/stacks-8-orange)](https://github.com/D1a0y1bb/CloverSec-CTF-Build-Dockerizer-skill)
[![Release Asset](https://img.shields.io/badge/release-zip-success)](https://github.com/D1a0y1bb/CloverSec-CTF-Build-Dockerizer-skill/releases/tag/v1.2.4)

A delivery-focused Skill for CTF Jeopardy challenges (Web / Pwn / AI). It standardizes challenge directories into platform-ready deliverables and enforces quality checks during generation.

## What's New in v1.2.4

- Added standalone bilingual docs: `README.md` (CN) and `README.en.md` (EN).
- Added real-world `Build_test` examples (Node / Python).
- Unified release workflow around `release_build.sh` and `publish_release.sh`.

<details>
<summary><b>v1.2.4 Key Deliverables</b></summary>

- Standard output triplet: `Dockerfile` / `start.sh` / `flag`
- Platform contract checks: `/start.sh`, `/flag`, `/bin/bash`, `EXPOSE`
- Reusable one-command install and publish process

</details>

## Core Capability Matrix

| Capability | Entry Script | Purpose | Output/Result |
|---|---|---|---|
| Auto Detection | `derive_config.py` | Detect stack, ports, start command candidates | Input basis for `CONFIG PROPOSAL` |
| Config Parsing | `parse_config_block.py` | Convert confirmation block to `challenge.yaml` | Normalized config |
| Render | `render.py` | Generate container delivery files | `Dockerfile` / `start.sh` / `flag` |
| Static Validation | `validate.sh` | Enforce platform contract and rules | ERROR/WARN/INFO report |
| Example Regression | `validate_examples.sh` | Batch-check sample directories | pass/fail summary |
| Packaging | `release_build.sh` | Build versioned folder and zip | `dist/...-vX.Y.Z.zip` |
| One-Command Publish | `publish_release.sh` | commit/tag/release/asset upload | downloadable GitHub Release |

## One-Command Install

```bash
npx -y skills add https://github.com/D1a0y1bb/CloverSec-CTF-Build-Dockerizer-skill --skill cloversec-ctf-build-dockerizer --agent codex -y
```

Verify installable skills from repository:

```bash
npx -y skills add https://github.com/D1a0y1bb/CloverSec-CTF-Build-Dockerizer-skill --list
```

## Quick Start

### AI-Orchestrated Flow (Recommended)

```text
Please use CloverSec-CTF-Build-Dockerizer for the current challenge directory.
Run auto-detection and output CONFIG PROPOSAL first; after I reply OK, generate Dockerfile/start.sh/flag and run validate.
```

Standard sequence:

1. Auto-detect (`derive_config.py`)
2. Confirm `CONFIG PROPOSAL`
3. Reply `OK` or edit YAML
4. Run `parse -> render -> validate`

### Manual Command Chain

```bash
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/derive_config.py --project-dir . --format json --pretty
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/render.py --config challenge.yaml --output .
bash src/CloverSec-CTF-Build-Dockerizer/scripts/validate.sh Dockerfile start.sh challenge.yaml
```

## Build_test Real Examples

The `Build_test` directory includes two challenge examples built and validated with this Skill:

| Case Name | Stack | Exposed Port | Start Command | Core Files |
|---|---|---:|---|---|
| `CTF-NodeJs RCE-Test1` | `node` | `3000` | `node app.js` | `challenge.yaml` / `Dockerfile` / `start.sh` / `app.js` |
| `CTF-Python沙箱逃逸-Test2` | `python` | `5000` | `python app.py` | `challenge.yaml` / `Dockerfile` / `start.sh` / `src/app.py` |

Validation commands:

```bash
# Node example
cd "Build_test/CTF-NodeJs RCE-Test1"
bash ../../src/CloverSec-CTF-Build-Dockerizer/scripts/validate.sh Dockerfile start.sh challenge.yaml

# Python example
cd "../CTF-Python沙箱逃逸-Test2"
bash ../../src/CloverSec-CTF-Build-Dockerizer/scripts/validate.sh Dockerfile start.sh challenge.yaml
```

Build and run examples:

```bash
# Node
cd "Build_test/CTF-NodeJs RCE-Test1"
docker build -t ctf-node-rce:latest .
docker run -d -p 13000:3000 ctf-node-rce:latest /start.sh

# Python
cd "../CTF-Python沙箱逃逸-Test2"
docker build -t ctf-python-sandbox:latest .
docker run -d -p 15000:5000 ctf-python-sandbox:latest /start.sh
```

<details>
<summary><b>Build_test commit policy</b></summary>

- Keep business example files for reproducibility.
- Remove metadata files (nested `.git` and `.DS_Store`).
- Skill discovery behavior (`npx skills add`) is unchanged.

</details>

## Platform Hard Constraints

Required before delivery:

1. Platform starts containers via `/start.sh`
2. `/flag` must exist at image root and be readable
3. `/bin/bash` must exist in image
4. Dockerfile must include `EXPOSE`
5. Idle keepalive patterns are forbidden (e.g., `sleep infinity`)
6. Single-service entry must run foreground via `exec`

Contract details: [platform_contract.md](src/CloverSec-CTF-Build-Dockerizer/docs/platform_contract.md)

## Supported Stacks

| Stack | Default Port | Start Example |
|---|---:|---|
| node | 3000 | `exec node server.js` |
| php | 80 | `exec apache2-foreground` |
| python | 5000 | `exec python app.py` / `exec gunicorn ...` |
| java | 8080 | `exec java -jar app.jar` |
| tomcat | 8080 | `exec catalina.sh run` |
| lamp | 80 | DB in background + Apache in foreground |
| pwn | 10000 | `exec /usr/sbin/xinetd -dontfork` |
| ai | 5000 | `exec gunicorn ...` |

## Repository Structure

```text
.
├── Build_test/
│   ├── CTF-NodeJs RCE-Test1/
│   └── CTF-Python沙箱逃逸-Test2/
├── src/CloverSec-CTF-Build-Dockerizer/
│   ├── SKILL.md
│   ├── data/
│   ├── templates/
│   ├── scripts/
│   ├── examples/
│   └── docs/
├── scripts/
│   ├── sync.sh
│   ├── doc_guard.sh
│   ├── release_build.sh
│   └── publish_release.sh
├── CHANGELOG.md
└── VERSION
```

## Release Workflow

```bash
# Standard packaging
bash scripts/release_build.sh

# One-command publish (commit/tag/release/asset)
bash scripts/publish_release.sh --version v1.2.4
```

## FAQ

### Q1: What is `Build_test` for?
It demonstrates real generation outputs and reproducible validation flow from this Skill.

### Q2: Does `npx skills add` require GitHub release assets?
No. It installs from repository content; release assets are for versioned download/archival.

### Q3: Why are `/start.sh`, `/flag`, and `/bin/bash` mandatory?
They are platform contract requirements. Missing any can break startup or dynamic flag injection.

## Maintenance and Contribution

Run at least these checks before PR/merge:

```bash
npx -y skills add . --list
bash scripts/release_build.sh --skip-checks
```

Maintained by CloverSec R&D Center.
