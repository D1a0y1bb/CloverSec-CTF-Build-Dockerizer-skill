# CloverSec-CTF-Build-Dockerizer

[简体中文](README.zh-CN.md) | [Legacy English Link](README.en.md)

[![Version](https://img.shields.io/badge/version-v1.2.4-blue)](https://github.com/D1a0y1bb/CloverSec-CTF-Build-Dockerizer-skill/releases)
[![Scope](https://img.shields.io/badge/CTF-Jeopardy-2ea44f)](https://github.com/D1a0y1bb/CloverSec-CTF-Build-Dockerizer-skill)
[![Stacks](https://img.shields.io/badge/stacks-8-orange)](https://github.com/D1a0y1bb/CloverSec-CTF-Build-Dockerizer-skill)
[![Release Asset](https://img.shields.io/badge/release-zip-success)](https://github.com/D1a0y1bb/CloverSec-CTF-Build-Dockerizer-skill/releases/tag/v1.2.4)

VERSION：v1.2.4

![CloverSec Overview](docs/assets/readme/hero-overview.png)

CloverSec-CTF-Build-Dockerizer is a delivery-focused skill for CTF Jeopardy challenges across Web, Pwn, and AI tracks. It transforms challenge directories into platform-ready artifacts and enforces contract checks so teams can move from authoring to release with reproducible quality instead of one-off manual fixes.

## What's New in v1.2.4

`v1.2.4` is the first public release and it is built around stability, not just feature count. The generation workflow now covers Pwn and AI challenge builds alongside Web, so all three tracks follow the same detect-render-validate path without fragmented scripts.

This release also resolves template-related failures that previously appeared in rendering and validation phases, and hardens multiple engineering paths such as error localization, edge-case script exits, and release chain consistency. The result is a workflow that can be reviewed, reproduced, and published as a standard team process.

<details>
<summary><b>v1.2.4 Technical hardening details</b></summary>

Three low-level contracts were tightened in this release: a normalized output triplet (`Dockerfile` / `start.sh` / `flag`), strict platform checks (`/start.sh`, `/flag`, `/bin/bash`, `EXPOSE`), and a converged release pipeline (`release_build.sh` + `publish_release.sh`) to reduce manual publishing drift.

</details>

## Core Capability Matrix

| Capability | Entry Script | Purpose | Output/Result |
|---|---|---|---|
| Auto Detection | `derive_config.py` | Detect stack, ports, and start-command candidates | Input basis for `CONFIG PROPOSAL` |
| Config Parsing | `parse_config_block.py` | Convert confirmation block to `challenge.yaml` | Normalized config |
| Render | `render.py` | Generate container delivery files | `Dockerfile` / `start.sh` / `flag` |
| Static Validation | `validate.sh` | Enforce platform contract and rules | ERROR/WARN/INFO report |
| Example Regression | `validate_examples.sh` | Batch-check sample directories | pass/fail summary |
| Packaging | `release_build.sh` | Build versioned folder and zip | `dist/...-vX.Y.Z.zip` |
| One-Command Publish | `publish_release.sh` | commit/tag/release/asset upload | downloadable GitHub Release |

## One-Command Install

Use Codex or Trae to install the skill in one command, then call it directly in your challenge workspace.

![Install with Codex or Trae](docs/assets/readme/install-codex-trae.png)

```bash
npx -y skills add https://github.com/D1a0y1bb/CloverSec-CTF-Build-Dockerizer-skill --skill cloversec-ctf-build-dockerizer --agent codex -y
```

If you want to verify skill discovery first:

```bash
npx -y skills add https://github.com/D1a0y1bb/CloverSec-CTF-Build-Dockerizer-skill --list
```

## Quick Start

### Agent-Orchestrated Flow

```text
Standard prompt: Please use CloverSec-CTF-Build-Dockerizer for the current challenge directory. Run auto-detection and output CONFIG PROPOSAL first; after I reply OK, generate Dockerfile/start.sh/flag and run validate.
```

This approach intentionally gates generation behind confirmation so stack assumptions and runtime contracts are aligned before artifacts are rendered. A shorter business prompt can trigger the same flow:

```text
Shortcut prompt: The src directory in this project is my Node.js CTF challenge. Please build it into a complete Docker image.
```

### Manual Command Chain

```bash
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/derive_config.py --project-dir . --format json --pretty
python3 src/CloverSec-CTF-Build-Dockerizer/scripts/render.py --config challenge.yaml --output .
bash src/CloverSec-CTF-Build-Dockerizer/scripts/validate.sh Dockerfile start.sh challenge.yaml
```

## Workflow Screenshots (Localized Assets)

Prompt entry:

![workflow-01](docs/assets/readme/workflow-01-quick-prompt.png)

Pre-build decision checkpoint:

![workflow-02](docs/assets/readme/workflow-02-prebuild-decision.png)

Error closure and follow-up:

![workflow-03](docs/assets/readme/workflow-03-error-closure.png)

Automatic artifact generation and build:

![workflow-04](docs/assets/readme/workflow-04-auto-build.png)

Automated acceptance tests:

![workflow-05](docs/assets/readme/workflow-05-auto-validation.png)

Hard acceptance checks:

![workflow-06](docs/assets/readme/workflow-06-hard-check.png)

Delivery checklist after validation:

![workflow-07](docs/assets/readme/workflow-07-delivery-checklist.png)

## Build_test Real Examples

`Build_test` includes two real challenge outputs generated and validated through this skill, so teams can run reproducible build and acceptance checks.

| Case Name | Stack | Exposed Port | Start Command | Core Files |
|---|---|---:|---|---|
| `CTF-NodeJs RCE-Test1` | `node` | `3000` | `node app.js` | `challenge.yaml` / `Dockerfile` / `start.sh` / `app.js` |
| `CTF-Python沙箱逃逸-Test2` | `python` | `5000` | `python app.py` | `challenge.yaml` / `Dockerfile` / `start.sh` / `challenge source app.py` |

Validation commands:

```bash
# Node example
cd "Build_test/CTF-NodeJs RCE-Test1"
bash ../../src/CloverSec-CTF-Build-Dockerizer/scripts/validate.sh Dockerfile start.sh challenge.yaml

# Python example
cd "../CTF-Python沙箱逃逸-Test2"
bash ../../src/CloverSec-CTF-Build-Dockerizer/scripts/validate.sh Dockerfile start.sh challenge.yaml
```

Build and run:

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
<summary><b>Build_test commit boundary</b></summary>

`Build_test` keeps reproducibility-critical business files (challenge code and delivery configs) while removing metadata that can break repository operations (nested `.git`, `.DS_Store`). This keeps collaboration stable without losing real examples.

</details>

## Platform Hard Constraints

Delivery artifacts must comply with platform contracts: containers are started from `/start.sh`; `/flag` must exist and be readable at image root; `/bin/bash` must be present; Dockerfile must declare `EXPOSE`; and idle keepalive patterns like `sleep infinity` are forbidden. For single-service targets, the entry process must run in foreground via `exec` to preserve signal handling and predictable exits.

Contract reference: [platform_contract.md](src/CloverSec-CTF-Build-Dockerizer/docs/platform_contract.md)

## Supported Stack Matrix

| Stack | Default Port | Start Example |
|---|---:|---|
| node | 3000 | `exec node server.js` |
| php | 80 | `exec apache2-foreground` |
| python | 5000 | `exec python app.py` / `exec gunicorn ...` |
| java | 8080 | `exec java -jar app.jar` |
| tomcat | 8080 | `exec catalina.sh run` |
| lamp | 80 | DB background + Apache foreground |
| pwn | 10000 | `exec /usr/sbin/xinetd -dontfork` |
| ai | 5000 | `exec gunicorn ...` |

## Repository Structure

```text
.
├── Build_test/
│   ├── CTF-NodeJs RCE-Test1/
│   └── CTF-Python沙箱逃逸-Test2/
├── docs/assets/readme/
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

## Changelog

See full version history in [CHANGELOG.md](CHANGELOG.md).

## FAQ

### Q1: What is `Build_test` for?
It provides real generated outputs and reproducible validation flows for PR review and delivery regression checks.

### Q2: Does `npx skills add` depend on GitHub Release assets?
No. `npx skills add` installs from repository content, while release assets are for versioned archival/distribution.

### Q3: Why are `/start.sh`, `/flag`, and `/bin/bash` mandatory?
They are platform contract requirements; missing any of them can break startup or dynamic flag injection.

## Maintenance and Contribution

Before PR/merge, run at least the checks below to ensure no regression in docs, skill discovery, and packaging pipeline:

```bash
npx -y skills add . --list
bash scripts/release_build.sh --skip-checks
```

Maintained by CloverSec R&D Center.

## License

This project is licensed under the [MIT License](LICENSE).
