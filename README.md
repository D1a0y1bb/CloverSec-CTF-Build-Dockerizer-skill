# CloverSec-CTF-Build-Dockerizer

<p align="center">
  <a href="README.zh-CN.md"><strong>简体中文</strong></a>
  <span> · </span>
  <a href="README.en.md"><strong>English</strong></a>
</p>


<p align="center">
  <img src="docs/assets/readme/CloverSec-CTF-Build-Dockerizer-skill.svg" alt="CloverSec-CTF-Build-Dockerizer-skill" width="920" />
</p>

<p align="center">
  <a href="https://github.com/D1a0y1bb/CloverSec-CTF-Build-Dockerizer-skill/releases"><img src="https://img.shields.io/badge/version-v1.4.0-2563eb?style=for-the-badge" alt="Version" /></a>
  <a href="https://github.com/D1a0y1bb/CloverSec-CTF-Build-Dockerizer-skill"><img src="https://img.shields.io/badge/CTF-Jeopardy-16a34a?style=for-the-badge" alt="Scope" /></a>
  <a href="https://github.com/D1a0y1bb/CloverSec-CTF-Build-Dockerizer-skill"><img src="https://img.shields.io/badge/stacks-9-f59e0b?style=for-the-badge" alt="Stacks" /></a>
  <a href="https://github.com/D1a0y1bb/CloverSec-CTF-Build-Dockerizer-skill/releases/tag/v1.4.0"><img src="https://img.shields.io/badge/release-zip-10b981?style=for-the-badge" alt="Release Asset" /></a>
</p>

<p align="center"><code><strong>VERSION</strong>: v1.4.0</code></p>

CloverSec-CTF-Build-Dockerizer is a delivery-focused skill for CTF challenge delivery across Web, Pwn, AI, and RDG(Docker) tracks. It transforms challenge directories into platform-ready artifacts and enforces contract checks so teams can move from authoring to release with reproducible quality instead of one-off manual fixes.

## What's New in v1.4.0

`v1.4.0` is an engine-level iteration focused on turning implicit assumptions into explicit contracts. The healthcheck field is now truly implemented: `challenge.healthcheck` is parsed, validated, and rendered into Docker `HEALTHCHECK`, with stack defaults from `stacks.yaml` and an explicit disable path.

Runtime compatibility is also tightened. `pwn` and `lamp` templates now support both Debian/Ubuntu and Alpine branches. Pwn can run with `xinetd` or fallback `tcpserver` (`ucspi-tcp6`) depending on base image capabilities, while LAMP can bootstrap Apache/PHP/MariaDB in both package ecosystems. This reduces base-image fragility when users override `base_image`.

Validation and orchestration are hardened for real delivery. `validate.sh` adds conditional localhost gates (`allow_loopback_bind` override + public-frontend-aware INFO pass), background-process exit-risk detection, and explicit start-port consistency hints against `EXPOSE` and `challenge.expose_ports`. `derive_config.py` now outputs `gates.requires_*` signals and can emit an empty start candidate for low-confidence/no-entry projects, preventing accidental auto-generation from weak evidence. Pattern coverage now includes FastAPI/Poetry, NestJS/pnpm workspace, and Spring Boot dynamic JAR paths.

<details>
<summary><b>v1.4.0 implementation highlights</b></summary>

New example coverage is added for `pwn-alpine-tcpserver-basic`, `lamp-alpine-basic`, and `python-loopback-ssrf-basic`. These examples validate Alpine runtime branches, SSRF loopback exemption (`platform.allow_loopback_bind=true`), and healthcheck disable behavior (`healthcheck.enabled=false`).

</details>

## Core Capability Matrix

| Capability | Entry Script | Purpose | Output/Result |
|---|---|---|---|
| Auto Detection | `derive_config.py` | Detect stack, ports, and start-command candidates | Input basis for `CONFIG PROPOSAL` |
| Config Parsing | `parse_config_block.py` | Convert confirmation block to `challenge.yaml` | Normalized config |
| Render | `render.py` | Generate container delivery files | `Dockerfile` / `start.sh` / `flag(optional)` / `check/check.sh` |
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
npm ci
bash ../../src/CloverSec-CTF-Build-Dockerizer/scripts/validate.sh Dockerfile start.sh challenge.yaml

# Python example
cd "../CTF-Python沙箱逃逸-Test2"
bash ../../src/CloverSec-CTF-Build-Dockerizer/scripts/validate.sh Dockerfile start.sh challenge.yaml
```

Build and run:

```bash
# Node
cd "Build_test/CTF-NodeJs RCE-Test1"
npm ci
docker build -t ctf-node-rce:latest .
docker run -d -p 13000:3000 ctf-node-rce:latest /start.sh

# Python
cd "../CTF-Python沙箱逃逸-Test2"
docker build -t ctf-python-sandbox:latest .
docker run -d -p 15000:5000 ctf-python-sandbox:latest /start.sh
```

<details>
<summary><b>Build_test commit boundary</b></summary>

`Build_test` keeps reproducibility-critical business files (challenge code and delivery configs) while removing metadata that can break repository operations (nested `.git`, `.DS_Store`). To control repository size and review noise, `Build_test/**/node_modules/` is not tracked; restore Node dependencies with `npm ci` when needed.

</details>

## RDG Regression Examples

Two RDG examples are included in `src/CloverSec-CTF-Build-Dockerizer/examples` for regression and CI coverage:

- `rdg-php-hardening-basic` (from PHP hardening challenge pattern)
- `rdg-python-ssti-basic` (from Python SSTI challenge pattern)

Both examples now cover `ttyd + sshd + check_service` defaults with executable check scripts. The Python example explicitly validates `include_flag_artifact=false` to cover non-flag scoring mode.

### RDG Toggle Example (Ops-Only Challenge)

For scenarios such as WebLogic maintenance challenges where player shell login is not required, you can disable both channels:

```yaml
challenge:
  stack: rdg
  rdg:
    enable_ttyd: false
    enable_sshd: false
    scoring_mode: check_service
    include_flag_artifact: false
    check_enabled: true
    check_script_path: "check/check.sh"
```

## Platform Hard Constraints

Delivery artifacts must comply with platform contracts: containers are started from `/start.sh`; `/bin/bash` must be present; Dockerfile must declare `EXPOSE`; and idle keepalive patterns like `sleep infinity` are forbidden. `/flag` is mandatory by default, with one RDG exception: `include_flag_artifact=false` for check-service-only challenge delivery. From `v1.4.0`, localhost binding is enforced by default with a controlled escape hatch: `challenge.platform.allow_loopback_bind=true`.

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
| pwn | 10000 | `exec /usr/sbin/xinetd -dontfork` / `exec tcpserver ...` |
| ai | 5000 | `exec gunicorn ...` |
| rdg | 80 / 22 / 8022 | `exec apache2-foreground` / `exec python app.py` |

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
bash scripts/publish_release.sh --version v1.4.0
```

## Changelog

See full version history in [CHANGELOG.md](CHANGELOG.md).

## FAQ

### Q1: What is `Build_test` for?
It provides real generated outputs and reproducible validation flows for PR review and delivery regression checks.

### Q2: Does `npx skills add` depend on GitHub Release assets?
No. `npx skills add` installs from repository content, while release assets are for versioned archival/distribution.

### Q3: Why are `/start.sh`, `/flag`, and `/bin/bash` mandatory?
They are platform contract requirements. In RDG mode, `/flag` can be explicitly disabled with `include_flag_artifact=false` when scoring is driven by check-service.

## Maintenance and Contribution

Before PR/merge, run at least the checks below to ensure no regression in docs, skill discovery, and packaging pipeline:

```bash
npx -y skills add . --list
bash scripts/release_build.sh --skip-checks
```

Maintained by CloverSec R&D Center.

## License

This project is licensed under the [MIT License](LICENSE).
